package instruction

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

type State string

const (
	StateAbsent      State = "absent"
	StateLinked      State = "linked"
	StateBroken      State = "broken"
	StateWrongTarget State = "wrong-target"
	StateRegular     State = "regular-file"
	StateDirectory   State = "directory"
	StateUnsupported State = "unsupported"
)

type SourceStatus string

const (
	SourceReady   SourceStatus = "ready"
	SourceMissing SourceStatus = "missing"
	SourceInvalid SourceStatus = "invalid"
)

type Status struct {
	Client        Client
	Source        string
	SourceStatus  SourceStatus
	State         State
	LinkType      string
	CurrentTarget string
}

type Action string

const (
	ActionSkip    Action = "skip"
	ActionLink    Action = "link"
	ActionReplace Action = "replace"
)

type Result struct {
	Action     Action
	BackupPath string
}

// Inspect は配置先を変更せず、現在のリンク状態だけを調べる。
func Inspect(source string, client Client) (Status, error) {
	normalizedSource, err := NormalizeSource(source)
	if err != nil {
		return Status{}, err
	}
	sourceStatus, err := InspectSource(normalizedSource)
	if err != nil {
		return Status{}, err
	}
	status := Status{
		Client:       client,
		Source:       normalizedSource,
		SourceStatus: sourceStatus,
		State:        StateAbsent,
	}

	info, err := os.Lstat(client.Path)
	if errors.Is(err, fs.ErrNotExist) {
		return status, nil
	}
	if err != nil {
		return Status{}, fmt.Errorf("instruction 配置先を調べられません (%s): %w", client.Path, err)
	}

	if info.Mode()&os.ModeSymlink != 0 {
		status.LinkType = "symlink"
		currentTarget, err := resolvedLinkTarget(client.Path)
		if err != nil {
			return Status{}, err
		}
		status.CurrentTarget = currentTarget
		targetMatchesSource, err := sameFile(currentTarget, normalizedSource)
		if err != nil {
			return Status{}, err
		}
		if samePath(currentTarget, normalizedSource) || targetMatchesSource {
			if sourceStatus == SourceReady {
				status.State = StateLinked
			} else {
				status.State = StateBroken
			}
			return status, nil
		}
		if _, err := os.Stat(client.Path); errors.Is(err, fs.ErrNotExist) {
			status.State = StateBroken
			return status, nil
		} else if err != nil {
			return Status{}, fmt.Errorf("instruction リンク先を調べられません (%s): %w", client.Path, err)
		}
		status.State = StateWrongTarget
		return status, nil
	}

	switch {
	case info.IsDir():
		status.LinkType = "directory"
		status.State = StateDirectory
	case info.Mode().IsRegular():
		status.LinkType = "regular-file"
		status.State = StateRegular
	default:
		status.LinkType = "unsupported"
		status.State = StateUnsupported
	}
	return status, nil
}

// InspectSource は source の存在と種別だけを調べる。source 不在はエラーにしない。
func InspectSource(source string) (SourceStatus, error) {
	normalizedSource, err := NormalizeSource(source)
	if err != nil {
		return "", err
	}
	info, err := os.Stat(normalizedSource)
	if errors.Is(err, fs.ErrNotExist) {
		return SourceMissing, nil
	}
	if err != nil {
		return "", fmt.Errorf("instruction source を調べられません (%s): %w", normalizedSource, err)
	}
	if !info.Mode().IsRegular() {
		return SourceInvalid, nil
	}
	return SourceReady, nil
}

// SourceStatusLabel は CLI 表示用の source 状態名を返す。
func SourceStatusLabel(status SourceStatus) string {
	switch status {
	case SourceReady:
		return "利用可能"
	case SourceMissing:
		return "見つかりません"
	case SourceInvalid:
		return "通常ファイルではありません"
	default:
		return string(status)
	}
}

// NeedsReplacement は、通常ファイルまたは別のリンクをバックアップして置き換えられる状態かを返す。
func NeedsReplacement(state State) bool {
	switch state {
	case StateBroken, StateWrongTarget, StateRegular:
		return true
	default:
		return false
	}
}

// NeedsRepair は、既存の symlink を修復できる状態かを返す。
// 通常ファイルや未配置の入口は repair の対象にせず、link の確認付き処理へ委ねる。
func NeedsRepair(state State) bool {
	return state == StateBroken || state == StateWrongTarget
}

// StateLabel は CLI 表示用の状態名を返す。
func StateLabel(state State) string {
	switch state {
	case StateAbsent:
		return "未配置"
	case StateLinked:
		return "リンク済み"
	case StateBroken:
		return "壊れたリンク"
	case StateWrongTarget:
		return "別の source へのリンク"
	case StateRegular:
		return "通常ファイル"
	case StateDirectory:
		return "ディレクトリ"
	case StateUnsupported:
		return "未対応の配置"
	default:
		return string(state)
	}
}

// ActionLabel は CLI 表示用の操作名を返す。
func ActionLabel(action Action) string {
	switch action {
	case ActionSkip:
		return "変更なし"
	case ActionLink:
		return "リンク作成"
	case ActionReplace:
		return "バックアップ後にリンク置換"
	default:
		return string(action)
	}
}

// BackupPath は、対象の隣に作るバックアップ名を返す。
func BackupPath(target string, now time.Time) string {
	base := target + ".mcp-docker-backup-" + now.UTC().Format("20060102T150405.000000000Z")
	candidate := base
	for suffix := 1; ; suffix++ {
		if _, err := os.Lstat(candidate); err != nil {
			return candidate
		}
		candidate = fmt.Sprintf("%s.%d", base, suffix)
	}
}

// Link は source への symlink を作成する。既存の通常ファイル／リンクは backupPath へ保全し、
// staging へ移した配置先の実体を再確認してから、作成専用の symlink で更新する。
// ディレクトリや未対応のファイル種別は置き換えない。
func Link(source string, client Client, now time.Time) (Result, error) {
	return link(source, client, now, nil)
}

// link は、競合状態をテストで再現できるよう置換直前のフックを受け取る。
func link(source string, client Client, now time.Time, beforeReplace func() error) (Result, error) {
	normalizedSource, err := ValidateSource(source)
	if err != nil {
		return Result{}, err
	}

	status, err := Inspect(normalizedSource, client)
	if err != nil {
		return Result{}, err
	}
	if status.State == StateLinked {
		return Result{Action: ActionSkip}, nil
	}
	if err := rejectSameSourceTarget(normalizedSource, client.Path); err != nil {
		return Result{}, err
	}
	if status.State == StateDirectory {
		return Result{}, fmt.Errorf("instruction 配置先はディレクトリのため置き換えません: %s", client.Path)
	}
	if status.State == StateUnsupported {
		return Result{}, fmt.Errorf("instruction 配置先は未対応のファイル種別のため置き換えません: %s", client.Path)
	}

	if err := os.MkdirAll(filepath.Dir(client.Path), 0o700); err != nil {
		return Result{}, fmt.Errorf("instruction 配置先の親ディレクトリを作成できません (%s): %w", filepath.Dir(client.Path), err)
	}

	if status.State == StateAbsent {
		if err := os.Symlink(normalizedSource, client.Path); err != nil {
			return Result{}, fmt.Errorf("instruction の symlink を作成できません (%s -> %s): %w", client.Path, normalizedSource, err)
		}
		return Result{Action: ActionLink}, nil
	}

	backupPath := BackupPath(client.Path, now)
	linkPath, err := temporaryLinkPath(client.Path, now)
	if err != nil {
		return Result{}, err
	}
	if err := os.Symlink(normalizedSource, linkPath); err != nil {
		return Result{}, fmt.Errorf("instruction の一時 symlink を作成できません (%s -> %s): %w", linkPath, normalizedSource, err)
	}

	expectedInfo, err := backupTarget(client.Path, backupPath)
	if err != nil {
		_ = os.Remove(linkPath)
		return Result{}, err
	}

	if err := replaceTarget(linkPath, client.Path, expectedInfo, now, beforeReplace); err != nil {
		cleanupErr := os.Remove(linkPath)
		if cleanupErr != nil {
			return Result{}, fmt.Errorf("instruction 配置先の安全な置換に失敗し、作業ファイルの掃除にも失敗しました (%s): %w", client.Path, errors.Join(err, cleanupErr))
		}
		return Result{}, err
	}

	return Result{Action: ActionReplace, BackupPath: backupPath}, nil
}

func rejectSameSourceTarget(source, target string) error {
	if samePath(source, target) {
		return fmt.Errorf("instruction source と配置先が同じです: %s", target)
	}
	same, err := sameFile(source, target)
	if err != nil {
		return fmt.Errorf("instruction source と配置先の実体を確認できません (%s, %s): %w", source, target, err)
	}
	if same {
		return fmt.Errorf("instruction source と配置先が同じ実体です: %s", target)
	}
	return nil
}

func sameFile(left, right string) (bool, error) {
	leftInfo, err := os.Stat(left)
	if errors.Is(err, fs.ErrNotExist) {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("ファイル実体を調べられません (%s): %w", left, err)
	}
	rightInfo, err := os.Stat(right)
	if errors.Is(err, fs.ErrNotExist) {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("ファイル実体を調べられません (%s): %w", right, err)
	}
	return os.SameFile(leftInfo, rightInfo), nil
}

func temporaryPath(target, kind string, now time.Time) (string, error) {
	base := target + ".mcp-docker-" + kind + "-" + now.UTC().Format("20060102T150405.000000000Z")
	candidate := base
	for attempt := 1; ; attempt++ {
		_, err := os.Lstat(candidate)
		if errors.Is(err, fs.ErrNotExist) {
			return candidate, nil
		}
		if err != nil {
			return "", fmt.Errorf("instruction の一時 %s 配置先を確認できません (%s): %w", kind, candidate, err)
		}
		candidate = fmt.Sprintf("%s.%d", base, attempt)
	}
}

func temporaryLinkPath(target string, now time.Time) (string, error) {
	return temporaryPath(target, "link", now)
}

func temporaryStagingPath(target string, now time.Time) (string, error) {
	path, err := temporaryPath(target, "staging", now)
	if err != nil {
		return "", err
	}
	return path, nil
}

func backupTarget(target, backupPath string) (fs.FileInfo, error) {
	info, err := os.Lstat(target)
	if errors.Is(err, fs.ErrNotExist) {
		return nil, fmt.Errorf("instruction 配置先が置換前に消えました: %s", target)
	}
	if err != nil {
		return nil, fmt.Errorf("instruction 配置先を再検証できません (%s): %w", target, err)
	}
	if info.IsDir() {
		return nil, fmt.Errorf("instruction 配置先はディレクトリのため置き換えません: %s", target)
	}
	switch {
	case info.Mode()&os.ModeSymlink != 0:
		linkTarget, err := os.Readlink(target)
		if err != nil {
			return nil, fmt.Errorf("既存の instruction symlink をバックアップできません (%s): %w", target, err)
		}
		if err := os.Symlink(linkTarget, backupPath); err != nil {
			return nil, fmt.Errorf("既存の instruction symlink をバックアップできません (%s -> %s): %w", target, backupPath, err)
		}
	case info.Mode().IsRegular():
		if err := os.Link(target, backupPath); err != nil {
			return nil, fmt.Errorf("既存の instruction ファイルをバックアップできません (%s -> %s): %w", target, backupPath, err)
		}
	default:
		return nil, fmt.Errorf("instruction 配置先は未対応のファイル種別のため置き換えません: %s", target)
	}
	return info, nil
}

func replaceTarget(linkPath, target string, expectedInfo fs.FileInfo, now time.Time, beforeRename func() error) error {
	currentInfo, err := os.Lstat(target)
	if errors.Is(err, fs.ErrNotExist) {
		return fmt.Errorf("instruction 配置先が再検証中に消えました: %s", target)
	}
	if err != nil {
		return fmt.Errorf("instruction 配置先を置換直前に再検証できません (%s): %w", target, err)
	}
	if currentInfo.IsDir() {
		return fmt.Errorf("instruction 配置先がディレクトリへ変化したため置き換えません: %s", target)
	}
	if currentInfo.Mode() != expectedInfo.Mode() || !os.SameFile(currentInfo, expectedInfo) {
		return fmt.Errorf("instruction 配置先が検証後に変化したため置き換えません: %s", target)
	}
	if beforeRename != nil {
		if err := beforeRename(); err != nil {
			return err
		}
	}

	stagingPath, err := temporaryStagingPath(target, now)
	if err != nil {
		return err
	}
	if err := os.Rename(target, stagingPath); err != nil {
		return fmt.Errorf("instruction 配置先を staging へ移動できません (%s -> %s): %w", target, stagingPath, err)
	}

	stagedInfo, err := os.Lstat(stagingPath)
	if err != nil {
		return fmt.Errorf("instruction staging の配置を再検証できません (%s): %w", stagingPath, err)
	}
	if stagedInfo.IsDir() || stagedInfo.Mode() != expectedInfo.Mode() || !os.SameFile(stagedInfo, expectedInfo) {
		if restoreErr := restoreStagedEntry(stagingPath, target); restoreErr != nil {
			return fmt.Errorf("instruction 配置先が検証後に変化し、staging の復元にも失敗しました (%s): %w", stagingPath, errors.Join(
				fmt.Errorf("expected entry と異なる配置を検出しました"),
				restoreErr,
			))
		}
		return fmt.Errorf("instruction 配置先が検証後に変化したため置き換えません: %s", target)
	}

	linkTarget, err := os.Readlink(linkPath)
	if err != nil {
		return fmt.Errorf("instruction の一時 symlink を読み込めません (%s): %w", linkPath, err)
	}
	if err := os.Symlink(linkTarget, target); err != nil {
		if restoreErr := restoreStagedEntry(stagingPath, target); restoreErr != nil {
			return fmt.Errorf("instruction の symlink 作成に失敗し、元の配置の復元にも失敗しました (%s): %w", target, errors.Join(err, restoreErr))
		}
		return fmt.Errorf("instruction の symlink を作成できません (%s -> %s): %w", target, linkTarget, err)
	}
	if err := os.Remove(linkPath); err != nil {
		return fmt.Errorf("instruction の一時 symlink を削除できません (%s): %w", linkPath, err)
	}
	if err := os.Remove(stagingPath); err != nil {
		return fmt.Errorf("instruction staging を削除できません (%s): %w", stagingPath, err)
	}
	return nil
}

func restoreStagedEntry(stagingPath, target string) error {
	if _, err := os.Lstat(target); err == nil {
		return fmt.Errorf("配置先に別の entry が存在するため staging を残しました: %s", stagingPath)
	} else if !errors.Is(err, fs.ErrNotExist) {
		return fmt.Errorf("staging 復元前に配置先を確認できません (%s): %w", target, err)
	}

	info, err := os.Lstat(stagingPath)
	if err != nil {
		return fmt.Errorf("staging を調べられません (%s): %w", stagingPath, err)
	}
	switch {
	case info.Mode()&os.ModeSymlink != 0:
		linkTarget, err := os.Readlink(stagingPath)
		if err != nil {
			return fmt.Errorf("staging symlink を読み込めません (%s): %w", stagingPath, err)
		}
		if err := os.Symlink(linkTarget, target); err != nil {
			return fmt.Errorf("staging symlink を復元できません (%s -> %s): %w", stagingPath, target, err)
		}
	case info.Mode().IsRegular():
		if err := os.Link(stagingPath, target); err != nil {
			return fmt.Errorf("staging ファイルを復元できません (%s -> %s): %w", stagingPath, target, err)
		}
	case info.IsDir():
		if err := os.Rename(stagingPath, target); err != nil {
			return fmt.Errorf("staging ディレクトリを復元できません (%s -> %s): %w", stagingPath, target, err)
		}
		return nil
	default:
		return fmt.Errorf("staging は未対応のファイル種別のため復元できません: %s", stagingPath)
	}
	if err := os.Remove(stagingPath); err != nil {
		return fmt.Errorf("復元済み staging を削除できません (%s): %w", stagingPath, err)
	}
	return nil
}

func resolvedLinkTarget(path string) (string, error) {
	target, err := os.Readlink(path)
	if err != nil {
		return "", fmt.Errorf("instruction symlink のリンク先を読み込めません (%s): %w", path, err)
	}
	if !filepath.IsAbs(target) {
		target = filepath.Join(filepath.Dir(path), target)
	}
	abs, err := filepath.Abs(target)
	if err != nil {
		return "", fmt.Errorf("instruction symlink のリンク先を解決できません (%s): %w", path, err)
	}
	return filepath.Clean(abs), nil
}

func samePath(left, right string) bool {
	leftAbs, leftErr := filepath.Abs(left)
	rightAbs, rightErr := filepath.Abs(right)
	if leftErr == nil && rightErr == nil {
		left = filepath.Clean(leftAbs)
		right = filepath.Clean(rightAbs)
	}
	if runtime.GOOS == "windows" {
		return strings.EqualFold(left, right)
	}
	return left == right
}
