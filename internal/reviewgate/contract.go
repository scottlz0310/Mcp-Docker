// Package reviewgate は reviewed-side のレビュー完了記録と停止契約を扱う。
package reviewgate

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"regexp"
	"strings"
	"unicode"
)

const (
	// ContractVersion は完了記録の JSON 契約バージョン。
	ContractVersion = 1

	// ReviewedSideSkillID は merge 前に必ず解決・実行する skill の識別子。
	ReviewedSideSkillID = "review-raven-thread-owl-cycle"
)

// StopCode は reviewed-side の fail-closed 停止理由。
type StopCode string

const (
	// StopSkillUnavailable は正本 skill を解決・読み込みできないことを表す。
	StopSkillUnavailable StopCode = "SKILL_UNAVAILABLE"
	// StopCompletionRecordInvalid は完了記録の形式または契約違反を表す。
	StopCompletionRecordInvalid StopCode = "COMPLETION_RECORD_INVALID"
	// StopReviewStatusMismatch は通知の status、URI、PR が一致しないことを表す。
	StopReviewStatusMismatch StopCode = "REVIEW_STATUS_MISMATCH"
	// StopHeadMismatch はレビュー対象、完了記録、CI の HEAD が一致しないことを表す。
	StopHeadMismatch StopCode = "HEAD_MISMATCH"
	// StopReviewIncomplete は返信または resolve が完了していないことを表す。
	StopReviewIncomplete StopCode = "REVIEW_INCOMPLETE"
	// StopCINotGreen は固定 HEAD の必須 CI が完了・成功していないことを表す。
	StopCINotGreen StopCode = "CI_NOT_GREEN"
)

var shaPattern = regexp.MustCompile(`^[0-9a-f]{40}$`)

// StopError は fail-closed で停止した理由を機械的に分類するエラー。
type StopError struct {
	Code    StopCode
	Field   string
	Message string
	Cause   error
}

func (e *StopError) Error() string {
	if e.Field == "" {
		if e.Cause == nil {
			return fmt.Sprintf("%s: %s", e.Code, e.Message)
		}
		return fmt.Sprintf("%s: %s: %v", e.Code, e.Message, e.Cause)
	}
	if e.Cause == nil {
		return fmt.Sprintf("%s: %s: %s", e.Code, e.Field, e.Message)
	}
	return fmt.Sprintf("%s: %s: %s: %v", e.Code, e.Field, e.Message, e.Cause)
}

// Unwrap は元の JSON 解析エラーなどを呼び出し側から検査できるようにする。
func (e *StopError) Unwrap() error {
	return e.Cause
}

func stop(code StopCode, field, message string) error {
	return &StopError{Code: code, Field: field, Message: message}
}

func invalid(field, message string) error {
	return stop(StopCompletionRecordInvalid, field, message)
}

// CompletionRecord は reviewed-side skill が同一 HEAD に対して生成する完了記録。
//
// この記録は merge の唯一の根拠ではなく、後続の merge gate が current PR、
// review threads、required checks と突き合わせるための証跡である。
type CompletionRecord struct {
	ContractVersion int         `json:"contractVersion"`
	Repo            string      `json:"repo"`
	PRNumber        int         `json:"prNumber"`
	HeadSHA         string      `json:"headSha"`
	SkillID         string      `json:"skillId"`
	SkillRevision   int         `json:"skillRevision"`
	SkillCompleted  bool        `json:"skillCompleted"`
	AllReplied      bool        `json:"all_replied"`
	UnresolvedCount int         `json:"unresolved_count"`
	CI              FixedHeadCI `json:"ci"`
}

// FixedHeadCI は完了記録に含める固定 HEAD の必須 check runs である。
type FixedHeadCI struct {
	HeadSHA        string     `json:"headSha"`
	Complete       bool       `json:"complete"`
	RequiredChecks []CheckRun `json:"requiredChecks"`
}

// CheckRun は固定 HEAD 上の 1 件の必須 check run である。
type CheckRun struct {
	Name       string `json:"name"`
	HeadSHA    string `json:"headSha"`
	Status     string `json:"status"`
	Conclusion string `json:"conclusion"`
}

// DecodeCompletionRecord は厳格な JSON として完了記録を読み込む。
// 未知フィールド、重複キー、JSON の連結を拒否し、曖昧な証跡を後続処理へ渡さない。
func DecodeCompletionRecord(data []byte) (CompletionRecord, error) {
	if err := rejectDuplicateJSONKeys(data); err != nil {
		return CompletionRecord{}, &StopError{
			Code:    StopCompletionRecordInvalid,
			Field:   "json",
			Message: "重複キーまたは不正な JSON を検出しました",
			Cause:   err,
		}
	}

	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()

	var record CompletionRecord
	if err := decoder.Decode(&record); err != nil {
		return CompletionRecord{}, &StopError{
			Code:    StopCompletionRecordInvalid,
			Field:   "json",
			Message: "完了記録を解析できません",
			Cause:   err,
		}
	}

	var extra json.RawMessage
	if err := decoder.Decode(&extra); !errors.Is(err, io.EOF) {
		if err == nil {
			return CompletionRecord{}, invalid("json", "JSON 値が複数あります")
		}
		return CompletionRecord{}, &StopError{
			Code:    StopCompletionRecordInvalid,
			Field:   "json",
			Message: "末尾の JSON を解析できません",
			Cause:   err,
		}
	}

	if err := record.Validate(); err != nil {
		return CompletionRecord{}, err
	}
	return record, nil
}

func rejectDuplicateJSONKeys(data []byte) error {
	decoder := json.NewDecoder(bytes.NewReader(data))
	if err := walkJSONValue(decoder, "$"); err != nil {
		return err
	}

	var extra json.RawMessage
	if err := decoder.Decode(&extra); err != io.EOF {
		if err == nil {
			return errors.New("JSON 値が複数あります")
		}
		return fmt.Errorf("末尾の JSON を解析できません: %w", err)
	}
	return nil
}

func walkJSONValue(decoder *json.Decoder, path string) error {
	token, err := decoder.Token()
	if err != nil {
		return err
	}

	delimiter, ok := token.(json.Delim)
	if !ok {
		return nil
	}

	switch delimiter {
	case '{':
		seen := make(map[string]struct{})
		for decoder.More() {
			keyToken, err := decoder.Token()
			if err != nil {
				return err
			}
			key, ok := keyToken.(string)
			if !ok {
				return errors.New("JSON オブジェクトのキーを解析できません")
			}
			if _, exists := seen[key]; exists {
				return fmt.Errorf("JSON オブジェクト %s に重複キー %q があります", path, key)
			}
			seen[key] = struct{}{}
			if err := walkJSONValue(decoder, path+"."+key); err != nil {
				return err
			}
		}
		end, err := decoder.Token()
		if err != nil {
			return err
		}
		if end != json.Delim('}') {
			return errors.New("JSON オブジェクトの終端を解析できません")
		}
	case '[':
		index := 0
		for decoder.More() {
			if err := walkJSONValue(decoder, fmt.Sprintf("%s[%d]", path, index)); err != nil {
				return err
			}
			index++
		}
		end, err := decoder.Token()
		if err != nil {
			return err
		}
		if end != json.Delim(']') {
			return errors.New("JSON 配列の終端を解析できません")
		}
	default:
		return fmt.Errorf("予期しない JSON delimiter %q", delimiter)
	}
	return nil
}

// Validate は完了記録が reviewed-side merge gate の入力契約を満たすか検証する。
func (r CompletionRecord) Validate() error {
	if r.ContractVersion != ContractVersion {
		return invalid("contractVersion", fmt.Sprintf("%d ではなく %d が必要です", r.ContractVersion, ContractVersion))
	}
	if !validRepo(r.Repo) {
		return invalid("repo", "owner/repository 形式が必要です")
	}
	if r.PRNumber < 1 {
		return invalid("prNumber", "1 以上が必要です")
	}
	if !shaPattern.MatchString(r.HeadSHA) {
		return invalid("headSha", "40 桁の小文字 hexadecimal が必要です")
	}
	if r.SkillID != ReviewedSideSkillID {
		return stop(StopSkillUnavailable, "skillId", fmt.Sprintf("%q は reviewed-side の正本ではありません", r.SkillID))
	}
	if r.SkillRevision < 1 {
		return stop(StopSkillUnavailable, "skillRevision", "正本 skill の revision がありません")
	}
	if r.UnresolvedCount < 0 {
		return invalid("unresolved_count", "0 以上が必要です")
	}
	if !r.SkillCompleted || !r.AllReplied || r.UnresolvedCount != 0 {
		return stop(StopReviewIncomplete, "review", "skill 完了、全返信、未解決スレッド 0 件が必要です")
	}
	if r.CI.HeadSHA != r.HeadSHA {
		return stop(StopHeadMismatch, "ci.headSha", "完了記録の HEAD と一致しません")
	}
	if !r.CI.Complete {
		return stop(StopCINotGreen, "ci.complete", "固定 HEAD の必須 CI が完了していません")
	}
	if len(r.CI.RequiredChecks) == 0 {
		return stop(StopCINotGreen, "ci.requiredChecks", "必須 check run がありません")
	}

	seen := make(map[string]struct{}, len(r.CI.RequiredChecks))
	for i, check := range r.CI.RequiredChecks {
		field := fmt.Sprintf("ci.requiredChecks[%d]", i)
		if strings.TrimSpace(check.Name) == "" {
			return invalid(field+".name", "空にできません")
		}
		if _, exists := seen[check.Name]; exists {
			return invalid(field+".name", "同じ check run が重複しています")
		}
		seen[check.Name] = struct{}{}
		if check.HeadSHA != r.HeadSHA {
			return stop(StopHeadMismatch, field+".headSha", "完了記録の HEAD と一致しません")
		}
		if check.Status != "completed" || check.Conclusion != "success" {
			return stop(StopCINotGreen, field, "status=completed かつ conclusion=success が必要です")
		}
	}
	return nil
}

func validRepo(repo string) bool {
	parts := strings.Split(repo, "/")
	if len(parts) != 2 || parts[0] == "" || parts[1] == "" {
		return false
	}
	for _, part := range parts {
		if strings.TrimSpace(part) != part || strings.IndexFunc(part, func(r rune) bool {
			return unicode.IsSpace(r) || unicode.IsControl(r)
		}) >= 0 || strings.ContainsRune(part, '\\') {
			return false
		}
	}
	return true
}
