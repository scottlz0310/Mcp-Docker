# ドキュメント整合性チェック機能

GitHub Actions Simulatorプロジェクトのドキュメント整合性を自動的にチェックし、品質を維持するためのツールです。

## 概要

ドキュメント整合性チェッカーは以下の機能を提供します：

1. **リンク有効性チェック**: ドキュメント間のリンクが正しく機能するかを確認
2. **バージョン整合性チェック**: プロジェクト全体でバージョン情報が一致しているかを確認
3. **内容整合性チェック**: 古い情報や矛盾する記述を検出

## 使用方法

### 基本的な使用方法

```bash
# 基本チェック
make check-docs

# または直接実行
uv run python scripts/check-docs-consistency.py
```

### 詳細オプション

```bash
# 詳細な情報を表示
uv run python scripts/check-docs-consistency.py --verbose

# 修正提案を表示
uv run python scripts/check-docs-consistency.py --fix-suggestions

# CI/CD環境向けの簡潔な出力
uv run python scripts/check-docs-consistency.py --ci-mode

# JSONレポートを出力
uv run python scripts/check-docs-consistency.py --output report.json

# 問題が見つかった場合にエラー終了
uv run python scripts/check-docs-consistency.py --fail-on-issues
```

## チェック項目

### 1. リンク有効性チェック

- **内部リンク**: 同一プロジェクト内のファイルへのリンクが存在するかを確認
- **アンカーリンク**: Markdownファイル内のヘッダーアンカーが存在するかを確認
- **相対パス**: 相対パスが正しく解決されるかを確認

#### 検出される問題例

```markdown
<!-- 例：壊れたリンク -->
[存在しないファイル](./nonexistent.md)  # テスト用の例：broken_link
[存在しないアンカー](../README.md#nonexistent-section)  # テスト用の例：broken_anchor
```

### 2. バージョン整合性チェック

プロジェクトのバージョン情報（`pyproject.toml`から取得）と、ドキュメント内のバージョン表記の整合性をチェックします。

#### 除外されるバージョン

以下のパターンは外部ツールのバージョンとして除外されます：

- Docker versions: `20.x.x`, `24.x.x`
- Docker Compose versions: `2.x.x`
- uv versions: `0.2.x`
- Development versions: `0.0.x`

#### 検出される問題例

```markdown
<!-- プロジェクトバージョンが1.1.0の場合 -->
Current version: 0.9.0  # version_mismatch
```

### 3. 内容整合性チェック

古い情報や推奨されない記述を検出します。

#### 検出される問題例

```bash
# 古い情報の例
# pip install package          # pip使用 → uvを使用してください
# npm install package          # npm使用 → 適切なパッケージマネージャーを使用
# requirements.txt             # requirements.txt → pyproject.tomlを使用

# 矛盾する記述の例
# Docker Desktop必須            # Docker Engineでも動作します
# root権限が必要               # rootless Dockerを推奨しています
```

## 設定ファイル

`.docs-check.yaml`ファイルでチェック動作をカスタマイズできます：

```yaml
# 除外するディレクトリ
exclude_dirs:
  - .git
  - .mypy_cache
  - archive

# バージョンチェック設定
version_check:
  exclude_patterns:
    - '^20\.\d+\.\d+$'    # Docker versions
    - '^0\.2\.\d+$'       # uv versions

# 整合性チェック設定
consistency_check:
  outdated_patterns:
    pip_usage:
      pattern: 'pip\s+install'
      message: "pip使用"
      suggestion: "uvを使用してください"
```

## 出力形式

### コンソール出力

```
📊 ドキュメント整合性チェック結果
⏰ 実行時刻: 2025-09-28T13:14:41.307923Z
📁 チェック対象ファイル数: 40
🚨 総問題数: 6

🔗 リンクの問題 (4件):
  ❌ docs/TROUBLESHOOTING.md:682
     リンク: \[クイックスタートガイド\](../README.md#クイックスタート)
     問題: リンク先ファイルが存在しません
```

### CI/CD向け出力

```
docs-check: 40 files, 6 issues
docs-check: CRITICAL - 4 broken links, 0 version mismatches
```

### JSON出力

```json
{
  "timestamp": "2025-09-28T13:14:41.307923Z",
  "total_files_checked": 40,
  "link_issues": [
    {
      "source_file": "docs/TROUBLESHOOTING.md",
      "line_number": 682,
      "link_text": "クイックスタートガイド",
      "target_path": "./QUICK_START.md",
      "issue_type": "broken_link",
      "description": "リンク先ファイルが存在しません"
    }
  ],
  "version_issues": [],
  "consistency_issues": []
}
```

## CI/CD統合

### GitHub Actions

`.github/workflows/docs-check.yml.sample`を参考に、GitHub Actionsワークフローに統合できます：

```yaml
- name: Run documentation consistency check
  run: |
    uv run python scripts/check-docs-consistency.py \
      --ci-mode \
      --fail-on-issues \
      --output docs-consistency-report.json
```

### pre-commit統合

`.pre-commit-config.yaml`に追加：

```yaml
repos:
  - repo: local
    hooks:
      - id: docs-consistency
        name: Documentation Consistency Check
        entry: uv run python scripts/check-docs-consistency.py
        args: [--fail-on-issues]
        language: system
        files: '\.md$'
```

## トラブルシューティング

### よくある問題

#### 1. 大量のバージョン不整合が報告される

**原因**: 外部ツールのバージョンがプロジェクトバージョンと混同されている

**解決方法**: `.docs-check.yaml`で除外パターンを追加

```yaml
version_check:
  exclude_patterns:
    - '^特定のバージョンパターン$'
```

#### 2. 正常なリンクが壊れていると報告される

**原因**: 相対パスの解釈が異なる

**解決方法**: リンクパスを確認し、プロジェクトルートからの正しい相対パスに修正

#### 3. 設定ファイルが読み込まれない

**原因**: 設定ファイルの形式が正しくない

**解決方法**: YAML形式を確認し、インデントを修正

```bash
# 設定ファイルの構文チェック
python -c "import yaml; yaml.safe_load(open('.docs-check.yaml'))"
```

### デバッグ方法

```bash
# 詳細ログで実行
uv run python scripts/check-docs-consistency.py --verbose

# 特定のファイルのみチェック
uv run python scripts/check-docs-consistency.py --root ./docs

# 設定ファイルを指定
uv run python scripts/check-docs-consistency.py --config ./custom-config.yaml
```

## 開発者向け情報

### スクリプトの拡張

新しいチェック機能を追加する場合：

1. `DocumentationChecker`クラスに新しいメソッドを追加
2. 対応する問題クラス（`@dataclass`）を定義
3. `generate_report`メソッドで新しいチェックを呼び出し
4. `print_report`関数で結果を表示

### テスト

```bash
# 単体テスト実行
uv run python -m pytest tests/test_docs_consistency.py -v

# 統合テスト
make check-docs
```

## 関連ドキュメント

- [トラブルシューティングガイド](./TROUBLESHOOTING.md)
- [CLI リファレンス](./CLI_REFERENCE.md)
- [開発者ガイド](../CONTRIBUTING.md)
