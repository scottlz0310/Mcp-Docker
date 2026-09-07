package skill

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// State は 1 クライアント上の 1 skill の配置状態。
type State string

const (
	// StateAbsent は未配置。
	StateAbsent State = "未配置"
	// StateUpToDate はカタログと一致している。
	StateUpToDate State = "最新"
	// StateOutdated は mcp-docker が配置したが内容が古い。
	StateOutdated State = "古い"
	// StateModified は配置後にローカルで改変されている。
	StateModified State = "ローカル改変あり"
	// StateUnmanaged はマニフェストのない配置（手動コピー等）。
	StateUnmanaged State = "管理外"
)

// Action は install / uninstall で実行する操作。
type Action string

const (
	// ActionSkip は何もしない。
	ActionSkip Action = "スキップ"
	// ActionInstall は新規配置。
	ActionInstall Action = "新規配置"
	// ActionUpdate は mcp-docker 管理下の配置を更新する。
	ActionUpdate Action = "更新"
	// ActionAdopt は管理外の既存配置を上書きして管理下に置く。
	ActionAdopt Action = "上書き（管理外を引き取り）"
	// ActionRemove は配置を削除する。
	ActionRemove Action = "削除"
)

// Manifest は配置先に残す配置メタデータ。
type Manifest struct {
	Skill       string            `json:"skill"`
	Source      string            `json:"source"`
	Version     string            `json:"version"`
	ContentHash string            `json:"content_hash"`
	Files       map[string]string `json:"files"`
	InstalledAt string            `json:"installed_at"`
}

// Status は 1 クライアント上の 1 skill の配置状態。
type Status struct {
	Client string
	Skill  string
	Dir    string
	State  State
	// InstalledVersion はマニフェストに記録された mcp-docker のバージョン。管理外・未配置では空。
	InstalledVersion string
	// Obsolete はマニフェストに記録されているがカタログに存在しないファイル（相対パス）。
	Obsolete []string
}

// Plan は 1 クライアント上の 1 skill に対する操作計画。
type Plan struct {
	Status
	Action Action
	// Write は書き込むファイルの相対パス。
	Write []string
	// Delete は削除するファイルの相対パス。
	Delete []string
}

// NeedsConfirm は破壊的な確認をユーザーに求めるべきかを返す。
// 管理外の配置を上書きする場合と削除する場合は、mcp-docker が書いていない内容を失うため確認する。
func (p Plan) NeedsConfirm() bool {
	return p.Action == ActionAdopt || p.Action == ActionRemove
}

// Inspect は client 上の skill の配置状態を調べる。
func Inspect(client Client, s Skill) (Status, error) {
	dir := filepath.Join(client.Dir, s.Name)
	status := Status{Client: client.Name, Skill: s.Name, Dir: dir}

	info, err := os.Stat(dir)
	if errors.Is(err, fs.ErrNotExist) {
		status.State = StateAbsent
		return status, nil
	}
	if err != nil {
		return status, fmt.Errorf("%s の確認に失敗しました: %w", dir, err)
	}
	if !info.IsDir() {
		return status, fmt.Errorf("%s はディレクトリではありません", dir)
	}

	manifest, err := readManifest(dir)
	if err != nil {
		return status, err
	}

	installed, err := scanInstalled(dir)
	if err != nil {
		return status, err
	}

	if manifest == nil {
		status.State = StateUnmanaged
		return status, nil
	}
	status.InstalledVersion = manifest.Version
	status.Obsolete = obsoleteFiles(manifest.Files, installed, s)

	switch {
	case contentHash(installed) == s.ContentHash:
		status.State = StateUpToDate
	case manifest.ContentHash == s.ContentHash:
		// マニフェストは最新版を指しているのに実体が違う = 配置後に改変された。
		status.State = StateModified
	default:
		status.State = StateOutdated
	}
	return status, nil
}

// PlanInstall は Inspect の結果から install の計画を作る。
// force が真の場合、最新でも再配置する。
func PlanInstall(status Status, s Skill, force bool) Plan {
	plan := Plan{Status: status, Delete: status.Obsolete}

	switch status.State {
	case StateAbsent:
		plan.Action = ActionInstall
	case StateUnmanaged:
		plan.Action = ActionAdopt
	case StateUpToDate:
		if !force {
			plan.Action = ActionSkip
			plan.Delete = nil
			return plan
		}
		plan.Action = ActionUpdate
	default:
		plan.Action = ActionUpdate
	}

	for _, f := range s.Files {
		plan.Write = append(plan.Write, f.Path)
	}
	return plan
}

// PlanRemove は Inspect の結果から uninstall の計画を作る。
// 管理外の配置は force を指定しない限り削除しない。
func PlanRemove(status Status, force bool) Plan {
	plan := Plan{Status: status}
	switch status.State {
	case StateAbsent:
		plan.Action = ActionSkip
	case StateUnmanaged:
		if !force {
			plan.Action = ActionSkip
			return plan
		}
		plan.Action = ActionRemove
	default:
		plan.Action = ActionRemove
	}
	return plan
}

// Install は plan に従って skill を配置し、マニフェストを書き出す。
func Install(plan Plan, s Skill, version string, now time.Time) error {
	if plan.Action == ActionSkip {
		return nil
	}
	if err := os.MkdirAll(plan.Dir, 0o755); err != nil {
		return fmt.Errorf("%s の作成に失敗しました: %w", plan.Dir, err)
	}

	for _, rel := range plan.Delete {
		if err := removeRelative(plan.Dir, rel); err != nil {
			return err
		}
	}

	files := make(map[string]string, len(s.Files))
	for _, f := range s.Files {
		dest := filepath.Join(plan.Dir, filepath.FromSlash(f.Path))
		if err := os.MkdirAll(filepath.Dir(dest), 0o755); err != nil {
			return fmt.Errorf("%s の作成に失敗しました: %w", filepath.Dir(dest), err)
		}
		if err := os.WriteFile(dest, f.Data, 0o644); err != nil {
			return fmt.Errorf("%s の書き込みに失敗しました: %w", dest, err)
		}
		files[f.Path] = f.SHA256
	}

	manifest := Manifest{
		Skill:       s.Name,
		Source:      "mcp-docker",
		Version:     version,
		ContentHash: s.ContentHash,
		Files:       files,
		InstalledAt: now.UTC().Format(time.RFC3339),
	}
	return writeManifest(plan.Dir, manifest)
}

// Remove は plan に従って skill の配置ディレクトリを削除する。
func Remove(plan Plan) error {
	if plan.Action != ActionRemove {
		return nil
	}
	if err := os.RemoveAll(plan.Dir); err != nil {
		return fmt.Errorf("%s の削除に失敗しました: %w", plan.Dir, err)
	}
	return nil
}

func removeRelative(dir, rel string) error {
	target := filepath.Join(dir, filepath.FromSlash(rel))
	// マニフェストが壊れていても配置先の外へ削除が及ばないようにする。
	if inside, err := filepath.Rel(dir, target); err != nil || inside == ".." || strings.HasPrefix(inside, ".."+string(filepath.Separator)) {
		return fmt.Errorf("配置先 %s の外を指す削除対象です: %q", dir, rel)
	}
	if err := os.Remove(target); err != nil && !errors.Is(err, fs.ErrNotExist) {
		return fmt.Errorf("%s の削除に失敗しました: %w", target, err)
	}
	// 空になった中間ディレクトリを配置先直下まで遡って掃除する。
	for parent := filepath.Dir(target); parent != dir; parent = filepath.Dir(parent) {
		if err := os.Remove(parent); err != nil {
			return nil
		}
	}
	return nil
}

// obsoleteFiles は「mcp-docker が配置した（マニフェスト記載）」かつ「実際に残っている」が
// 「現在のカタログには無い」ファイルを返す。マニフェストに無いファイルはユーザー由来なので触らない。
func obsoleteFiles(recorded map[string]string, installed []File, s Skill) []string {
	current := make(map[string]struct{}, len(s.Files))
	for _, f := range s.Files {
		current[f.Path] = struct{}{}
	}
	var obsolete []string
	for _, f := range installed {
		if _, ok := recorded[f.Path]; !ok {
			continue
		}
		if _, ok := current[f.Path]; ok {
			continue
		}
		obsolete = append(obsolete, f.Path)
	}
	sort.Strings(obsolete)
	return obsolete
}

func readManifest(dir string) (*Manifest, error) {
	data, err := os.ReadFile(filepath.Join(dir, ManifestName))
	if errors.Is(err, fs.ErrNotExist) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("%s の読み込みに失敗しました: %w", filepath.Join(dir, ManifestName), err)
	}
	var manifest Manifest
	if err := json.Unmarshal(data, &manifest); err != nil {
		return nil, fmt.Errorf("%s の解析に失敗しました: %w", filepath.Join(dir, ManifestName), err)
	}
	return &manifest, nil
}

func writeManifest(dir string, manifest Manifest) error {
	data, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		return fmt.Errorf("マニフェストの生成に失敗しました: %w", err)
	}
	path := filepath.Join(dir, ManifestName)
	if err := os.WriteFile(path, append(data, '\n'), 0o644); err != nil {
		return fmt.Errorf("%s の書き込みに失敗しました: %w", path, err)
	}
	return nil
}

// scanInstalled は配置先の実ファイルを読み、カタログと同じ形式の File 一覧にする。
// マニフェストとドットで始まるエントリは skill の内容に含めない。
func scanInstalled(dir string) ([]File, error) {
	var files []File
	err := filepath.WalkDir(dir, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			if p != dir && strings.HasPrefix(d.Name(), ".") {
				return fs.SkipDir
			}
			return nil
		}
		if strings.HasPrefix(d.Name(), ".") {
			return nil
		}
		data, err := os.ReadFile(p)
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(dir, p)
		if err != nil {
			return err
		}
		files = append(files, File{Path: filepath.ToSlash(rel), Data: data, SHA256: hashBytes(data)})
		return nil
	})
	if err != nil {
		return nil, fmt.Errorf("%s の走査に失敗しました: %w", dir, err)
	}
	sort.Slice(files, func(i, j int) bool { return files[i].Path < files[j].Path })
	return files, nil
}
