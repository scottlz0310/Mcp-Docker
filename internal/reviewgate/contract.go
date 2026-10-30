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

	// RequiredChecksDefined は repository 設定から必須 check を1件以上確定できたことを表す。
	// requiredChecksPolicy を省略した場合も同じ扱いになる。
	RequiredChecksDefined = "defined"

	// RequiredChecksUndefined は repository 設定を読み取り、必須 check が未定義だと確認できたことを表す。
	// 設定を判定できなかった場合は含まない。その場合は完了記録を作らず停止する。
	RequiredChecksUndefined = "undefined"
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
	// StopReviewGateUnavailable は完了記録のローカル検証コマンドを実行できないことを表す。
	StopReviewGateUnavailable StopCode = "REVIEW_GATE_UNAVAILABLE"
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

// FixedHeadCI は完了記録に含める固定 HEAD の check runs である。
//
// 必須 check を repository 設定から確定できた場合は RequiredChecks に列挙する。
// 設定を読み取って必須 check が未定義だと確認できた場合だけ、RequiredChecksPolicy を
// RequiredChecksUndefined にし、固定 HEAD で観測した全 check run を ObservedChecks に列挙する。
// RequiredChecks が空であることだけでは、設定が未定義なのか判定できなかったのかを区別できないため、
// 空配列を「未定義」と解釈しない。
//
// 設計どおり skipped になる check（PR では実行しない job など）は、repository が名前を明示して許可した
// ものに限り、SkipPolicy と各 check の PolicyAllowedSkip で記録する。
type FixedHeadCI struct {
	HeadSHA              string      `json:"headSha"`
	Complete             bool        `json:"complete"`
	RequiredChecksPolicy string      `json:"requiredChecksPolicy,omitempty"`
	RequiredChecks       []CheckRun  `json:"requiredChecks"`
	ObservedChecks       []CheckRun  `json:"observedChecks,omitempty"`
	SkipPolicy           *SkipPolicy `json:"skipPolicy,omitempty"`
}

// SkipPolicy は repository が宣言した、skipped を許可する check の名前の一覧である。
//
// 宣言は PR の HEAD ではなく base ref のファイル（.review-raven/ci-policy.json）から読む。
// PR 自身が自分の skip を許可できないようにするためで、投稿者の allowlist と同じ信頼境界である。
// BaseSHA は、その宣言を読んだ base ref の SHA で、後から読み直して確認できるようにする。
// この検証器は形式と記録内の整合だけを確認し、宣言が base ref から読まれたことは確認できない
// （記録の作成手順を定める skill の責務）。
type SkipPolicy struct {
	BaseSHA              string   `json:"baseSha"`
	AllowedSkippedChecks []string `json:"allowedSkippedChecks"`
}

// ValidationTarget は完了記録を検証する直前に固定した外部状態を表す。
//
// 記録自身に含まれる値の整合性だけでなく、現在の PR と埋め込み skill の
// revision に結び付けることで、古い記録の再利用を防ぐ。
type ValidationTarget struct {
	Repo          string
	PRNumber      int
	HeadSHA       string
	SkillRevision int
}

// CheckRun は固定 HEAD 上の 1 件の check run である。
//
// CI の read は (App ID, name) ごとに再実行を集約するため、別の GitHub App が同名の check を
// 報告すると、同名の run が複数残る。AppID はそれらを区別する識別情報で、ObservedChecks では必須、
// RequiredChecks では省略できる（必須 check は context 単位で、同名を重複として扱う）。
//
// PolicyAllowedSkip は、conclusion が skipped の check が、SkipPolicy で許可された名前であることを明示する。
// skipped 以外の check には付けられない。
type CheckRun struct {
	Name              string `json:"name"`
	AppID             int64  `json:"appId,omitempty"`
	HeadSHA           string `json:"headSha"`
	Status            string `json:"status"`
	Conclusion        string `json:"conclusion"`
	PolicyAllowedSkip bool   `json:"policyAllowedSkip,omitempty"`
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
	allowedSkips, err := r.CI.allowedSkippedNames()
	if err != nil {
		return err
	}
	switch r.CI.RequiredChecksPolicy {
	case "", RequiredChecksDefined:
		if len(r.CI.ObservedChecks) != 0 {
			return invalid("ci.observedChecks", "requiredChecksPolicy が undefined のときだけ指定できます")
		}
		if len(r.CI.RequiredChecks) == 0 {
			return stop(StopCINotGreen, "ci.requiredChecks", "必須 check run がありません")
		}
		return validateGreenChecks("ci.requiredChecks", r.CI.RequiredChecks, r.HeadSHA, false, allowedSkips)
	case RequiredChecksUndefined:
		if len(r.CI.RequiredChecks) != 0 {
			return invalid("ci.requiredChecks", "requiredChecksPolicy が undefined のときは空にします")
		}
		if len(r.CI.ObservedChecks) == 0 {
			return stop(StopCINotGreen, "ci.observedChecks", "観測した check run がありません")
		}
		return validateGreenChecks("ci.observedChecks", r.CI.ObservedChecks, r.HeadSHA, true, allowedSkips)
	default:
		return invalid("ci.requiredChecksPolicy", fmt.Sprintf("%q は未対応です", r.CI.RequiredChecksPolicy))
	}
}

// checkIdentity は check run の同一性を判定する鍵である。
type checkIdentity struct {
	appID int64
	name  string
}

// allowedSkippedNames は SkipPolicy を検証し、skipped を許可された check の名前の集合を返す。
// SkipPolicy が無ければ空の集合を返す（skipped は 1 件も許可されない）。
func (ci FixedHeadCI) allowedSkippedNames() (map[string]struct{}, error) {
	allowed := map[string]struct{}{}
	if ci.SkipPolicy == nil {
		return allowed, nil
	}
	if !shaPattern.MatchString(ci.SkipPolicy.BaseSHA) {
		return nil, invalid("ci.skipPolicy.baseSha", "宣言を読んだ base ref の 40 桁の小文字 hexadecimal が必要です")
	}
	if len(ci.SkipPolicy.AllowedSkippedChecks) == 0 {
		return nil, invalid("ci.skipPolicy.allowedSkippedChecks", "1 件以上の check 名が必要です（許可しないなら skipPolicy ごと省略します）")
	}
	for i, name := range ci.SkipPolicy.AllowedSkippedChecks {
		item := fmt.Sprintf("ci.skipPolicy.allowedSkippedChecks[%d]", i)
		if strings.TrimSpace(name) == "" || strings.TrimSpace(name) != name {
			return nil, invalid(item, "空、または前後に空白のある名前は使えません")
		}
		if _, exists := allowed[name]; exists {
			return nil, invalid(item, "同じ名前が重複しています")
		}
		allowed[name] = struct{}{}
	}
	return allowed, nil
}

// validateGreenChecks は checks がすべて同一 HEAD 上で completed であり、success であることを検証する。
// ただし、allowedSkips に名前があり、policyAllowedSkip を付けた skipped の check は成功として扱う。
// skipped は「実質的な check が黙って動かなかった」場合と区別できないため、名前を明示して許可されたものに限り、
// success の check が 1 件以上あることも必須とする（すべてが skipped の記録は、何も検証していない）。
// byApp が true のときは App ID を必須とし、(App ID, name) で重複を判定する。false のときは name だけで判定する。
func validateGreenChecks(field string, checks []CheckRun, headSHA string, byApp bool, allowedSkips map[string]struct{}) error {
	seen := make(map[checkIdentity]struct{}, len(checks))
	successCount := 0
	for i, check := range checks {
		item := fmt.Sprintf("%s[%d]", field, i)
		if strings.TrimSpace(check.Name) == "" {
			return invalid(item+".name", "空にできません")
		}
		if check.AppID < 0 || (byApp && check.AppID < 1) {
			return invalid(item+".appId", "GitHub App の ID（1 以上）が必要です")
		}
		identity := checkIdentity{name: check.Name}
		if byApp {
			identity.appID = check.AppID
		}
		if _, exists := seen[identity]; exists {
			return invalid(item+".name", "同じ check run が重複しています")
		}
		seen[identity] = struct{}{}
		if check.HeadSHA != headSHA {
			return stop(StopHeadMismatch, item+".headSha", "完了記録の HEAD と一致しません")
		}
		if check.PolicyAllowedSkip {
			if check.Conclusion != "skipped" {
				return invalid(item+".policyAllowedSkip", "conclusion が skipped の check にだけ付けられます")
			}
			if _, ok := allowedSkips[check.Name]; !ok {
				return invalid(item+".policyAllowedSkip", "ci.skipPolicy.allowedSkippedChecks に名前がありません")
			}
		}
		if check.Status != "completed" {
			return stop(StopCINotGreen, item, "status=completed が必要です")
		}
		switch {
		case check.Conclusion == "success":
			successCount++
		case check.Conclusion == "skipped" && check.PolicyAllowedSkip:
			// repository が名前を明示して許可した skipped
		default:
			return stop(StopCINotGreen, item, "conclusion=success が必要です（skipped は ci.skipPolicy で許可した名前に policyAllowedSkip を付けたものだけ）")
		}
	}
	if successCount == 0 {
		return stop(StopCINotGreen, field, "conclusion=success の check が 1 件以上必要です")
	}
	return nil
}

// ValidateFor は完了記録を、直前に固定した PR と埋め込み skill に結び付けて検証する。
func (r CompletionRecord) ValidateFor(target ValidationTarget) error {
	if err := target.Validate(); err != nil {
		return err
	}
	if err := r.Validate(); err != nil {
		return err
	}
	if r.Repo != target.Repo || r.PRNumber != target.PRNumber {
		return stop(StopReviewStatusMismatch, "target", "完了記録の repository または PR が現在の対象と一致しません")
	}
	if r.HeadSHA != target.HeadSHA {
		return stop(StopHeadMismatch, "headSha", "完了記録の HEAD が現在の PR HEAD と一致しません")
	}
	if r.SkillRevision != target.SkillRevision {
		return stop(StopSkillUnavailable, "skillRevision", "完了記録の revision が埋め込み skill と一致しません")
	}
	return nil
}

// Validate は完了記録を結び付ける対象の値を検証する。
func (t ValidationTarget) Validate() error {
	if !validRepo(t.Repo) {
		return invalid("target.repo", "owner/repository 形式が必要です")
	}
	if t.PRNumber < 1 {
		return invalid("target.prNumber", "1 以上が必要です")
	}
	if !shaPattern.MatchString(t.HeadSHA) {
		return invalid("target.headSha", "40 桁の小文字 hexadecimal が必要です")
	}
	if t.SkillRevision < 1 {
		return invalid("target.skillRevision", "1 以上が必要です")
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
