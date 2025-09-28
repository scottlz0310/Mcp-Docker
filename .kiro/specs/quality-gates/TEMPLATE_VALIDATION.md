# テンプレート動作検証システム

GitHub Actions Simulator のテンプレート動作検証システムは、プロジェクト内の全テンプレートファイルの品質と動作を自動的に検証するシステムです。

## 概要

このシステムは以下の機能を提供します：

- **構文チェック**: YAML、JSON、Shell、Docker、環境変数ファイルの構文検証
- **機能テスト**: テンプレートの実際の動作確認
- **セキュリティチェック**: 秘密情報の検出と権限設定の確認
- **CI/CD統合**: 自動化されたパイプラインでの継続的検証

## 検証対象ファイル

### 環境変数テンプレート
- `.env.example` - 環境変数設定のサンプル

### Docker設定テンプレート
- `docker-compose.override.yml.sample` - Docker Compose カスタマイズ設定

### 開発ツール設定テンプレート
- `.pre-commit-config.yaml.sample` - pre-commit フック設定

### GitHub Actions ワークフローテンプレート
- `.github/workflows/local-ci.yml.sample` - ローカルCI用ワークフロー
- `.github/workflows/basic-test.yml.sample` - 基本テスト用ワークフロー
- `.github/workflows/security-scan.yml.sample` - セキュリティスキャン用ワークフロー

## 使用方法

### 基本的な使用方法

```bash
# 完全な検証（推奨）
make validate-templates

# 構文チェックのみ（高速）
make validate-templates-syntax

# 機能テストのみ
make validate-templates-functionality

# CI用検証（JSON出力）
make validate-templates-ci
```

### 詳細オプション付き実行

```bash
# 詳細ログ付きで実行
./scripts/ci-validate-templates.sh --verbose

# 構文チェックのみ
./scripts/ci-validate-templates.sh --check-only

# 機能テストのみ
./scripts/ci-validate-templates.sh --test-only

# JSON形式で結果出力
./scripts/ci-validate-templates.sh --format json --output report.json

# 高速失敗モード
./scripts/ci-validate-templates.sh --fail-fast
```

### Python スクリプト直接実行

```bash
# 基本的な検証
python3 scripts/validate-templates.py

# 構文チェックのみ
python3 scripts/validate-templates.py --check-only

# 機能テストのみ
python3 scripts/validate-templates.py --test-only

# 詳細ログ付き
python3 scripts/validate-templates.py --verbose

# JSON形式出力
python3 scripts/validate-templates.py --format json
```

## 検証内容

### 1. 構文チェック

#### YAML/YMLファイル
- YAML構文の正確性
- インデントの一貫性
- 特殊文字のエスケープ

#### JSONファイル
- JSON構文の正確性
- 括弧とクォートの対応
- 末尾カンマの検出

#### Shellスクリプト
- Bash構文の正確性（ShellCheck使用）
- 変数の適切な使用
- エラーハンドリングの確認

#### Dockerファイル
- Dockerfile構文の正確性（hadolint使用）
- ベストプラクティスの遵守
- セキュリティ設定の確認

#### 環境変数ファイル
- 変数名の形式チェック
- 値の適切なクォート
- 重複変数の検出

### 2. 機能テスト

#### Docker Compose テンプレート
```bash
# 設定の妥当性確認
docker-compose -f template.yml config

# サービス定義の検証
# 環境変数の展開テスト
```

#### GitHub Actions ワークフロー
```bash
# ワークフロー構造の検証
# 必須要素の存在確認
# act による実行可能性テスト（利用可能な場合）
```

#### pre-commit 設定
```bash
# 設定ファイルの妥当性確認
pre-commit validate-config template.yaml

# フック定義の検証
```

#### 環境変数ファイル
- 重要な変数の存在確認
- 変数の読み込みテスト
- デフォルト値の妥当性

### 3. セキュリティチェック

#### 秘密情報検出
- 実際のパスワード・トークンの検出
- APIキーの漏洩チェック
- プレースホルダーとの区別

#### 権限設定確認
- ファイル権限の適切性
- Docker特権モードの検出
- 危険なケーパビリティの確認

#### 設定の安全性
- デフォルト設定の安全性
- 本番環境での使用可能性

## 出力形式

### テキスト形式（デフォルト）

```
================================================================================
GitHub Actions Simulator - テンプレート検証レポート
================================================================================

🕐 実行時刻: 2024-01-15 10:30:45
⏱️ 実行時間: 2.34秒
📊 成功率: 95.0%

📋 サマリー:
  📁 総テンプレート数: 6
  ✅ 有効なテンプレート: 5
  ❌ 無効なテンプレート: 1
  ⚠️ 警告があるテンプレート: 2

📊 テンプレートタイプ別統計:
  env: 1/1 (100.0%)
  docker_compose: 1/1 (100.0%)
  precommit: 1/1 (100.0%)
  github_workflows: 2/3 (66.7%)

📋 詳細結果:
--------------------------------------------------------------------------------
✅ .env.example (env)
  ⏱️ 実行時間: 0.123秒

❌ .github/workflows/invalid.yml.sample (github_workflows)
  🔍 構文エラー:
    - YAML構文エラー: mapping values are not allowed here
  ⏱️ 実行時間: 0.456秒
```

### JSON形式

```json
{
  "total_templates": 6,
  "valid_templates": 5,
  "invalid_templates": 1,
  "templates_with_warnings": 2,
  "execution_time": 2.34,
  "results": [
    {
      "file_path": ".env.example",
      "template_type": "env",
      "syntax_valid": true,
      "syntax_errors": [],
      "functionality_valid": true,
      "functionality_errors": [],
      "security_issues": [],
      "warnings": [],
      "execution_time": 0.123
    }
  ]
}
```

## CI/CD統合

### GitHub Actions ワークフロー

プロジェクトには自動化されたテンプレート検証ワークフロー（`.github/workflows/template-validation.yml`）が含まれています。

#### 実行タイミング
- プルリクエスト時（テンプレートファイル変更時）
- メインブランチへのプッシュ時
- 定期実行（週次）
- 手動実行

#### ワークフロージョブ
1. **構文チェック** - 高速な構文検証
2. **機能テスト** - 実際の動作確認
3. **完全検証** - 構文+機能+セキュリティの包括的検証
4. **検証システムテスト** - 検証システム自体の動作確認

### ローカル開発での統合

#### pre-commit フック統合

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: template-validation
        name: "テンプレート検証"
        entry: ./scripts/ci-validate-templates.sh --check-only
        language: system
        files: \.(sample|example|template)$
```

#### Make ターゲット

```bash
# 開発時の検証
make validate-templates

# CI/CD パイプライン用
make validate-templates-ci

# レポート生成
make validate-templates-report
```

## 依存関係

### 必須依存関係
- Python 3.11+
- PyYAML
- pytest（テスト実行用）

### オプショナル依存関係
- **shellcheck** - Shell構文チェック
- **yamllint** - YAML品質チェック
- **hadolint** - Dockerfile品質チェック
- **docker** - Docker Compose機能テスト
- **act** - GitHub Actions ローカル実行
- **pre-commit** - pre-commit機能テスト

### インストール方法

```bash
# 基本依存関係
uv sync --group test --group dev

# Ubuntu/Debian でのオプショナルツール
sudo apt-get install shellcheck yamllint

# macOS でのオプショナルツール
brew install shellcheck yamllint hadolint

# hadolint（手動インストール）
wget -O /usr/local/bin/hadolint \
  https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64
chmod +x /usr/local/bin/hadolint
```

## トラブルシューティング

### よくある問題

#### 1. 依存関係不足エラー

```bash
❌ 必須の依存関係が不足しています: python3
```

**解決方法:**
```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-pip

# macOS
brew install python3

# 依存関係の再インストール
uv sync --group test --group dev
```

#### 2. 権限エラー

```bash
❌ ファイル権限が緩すぎる可能性があります
```

**解決方法:**
```bash
# ファイル権限の修正
chmod 644 .env.example
chmod 644 *.sample

# 権限チェックスクリプトの実行
./scripts/fix-permissions.sh
```

#### 3. Docker関連エラー

```bash
❌ Docker Compose設定エラー: service 'app' has neither an image nor a build context
```

**解決方法:**
```bash
# Docker環境の確認
docker --version
docker-compose --version

# 設定ファイルの検証
docker-compose -f docker-compose.override.yml.sample config
```

#### 4. YAML構文エラー

```bash
❌ YAML構文エラー: mapping values are not allowed here
```

**解決方法:**
```bash
# YAML構文の確認
yamllint file.yml.sample

# インデントの修正
# コロンの後にスペースを追加
# クォートの対応を確認
```

### デバッグ方法

#### 詳細ログの有効化

```bash
# 詳細ログ付きで実行
./scripts/ci-validate-templates.sh --verbose

# Python スクリプトでのデバッグ
python3 scripts/validate-templates.py --verbose
```

#### 個別ファイルのテスト

```bash
# 特定のファイルのみテスト
python3 -c "
from scripts.validate_templates import TemplateValidator
validator = TemplateValidator(verbose=True)
result = validator.validate_template(Path('.env.example'), 'env')
print(result)
"
```

#### 段階的なデバッグ

```bash
# 1. 構文チェックのみ
make validate-templates-syntax

# 2. 機能テストのみ
make validate-templates-functionality

# 3. 完全検証
make validate-templates
```

## カスタマイズ

### 検証ルールの追加

新しいテンプレートタイプを追加する場合：

```python
# scripts/validate-templates.py の template_patterns に追加
self.template_patterns = {
    'env': ['.env.example', '.env.template'],
    'docker_compose': ['docker-compose.*.yml.sample'],
    'precommit': ['.pre-commit-config.yaml.sample'],
    'github_workflows': ['.github/workflows/*.yml.sample'],
    'custom_type': ['*.custom.sample'],  # 新しいタイプ
}
```

### 除外パターンの設定

特定のファイルを検証から除外する場合：

```bash
# CI スクリプトの EXCLUDE_PATTERNS を編集
EXCLUDE_PATTERNS=(
    "*.backup.sample"
    "deprecated/*"
    "experimental/*.template"
)
```

### セキュリティルールのカスタマイズ

```python
# _validate_security メソッドでカスタムパターンを追加
secret_patterns = [
    (r'password\s*=\s*["\']?[^"\'\s#]+', '平文パスワードの可能性'),
    (r'custom_secret\s*=\s*["\']?[^"\'\s#]+', 'カスタム秘密情報'),  # 追加
]
```

## パフォーマンス最適化

### 高速実行のコツ

```bash
# 構文チェックのみで高速実行
make validate-templates-syntax

# 並列実行（将来の機能）
./scripts/ci-validate-templates.sh --parallel

# キャッシュの活用
export UV_CACHE_DIR=/tmp/.uv-cache
```

### CI/CD での最適化

```yaml
# GitHub Actions でのキャッシュ活用
- name: Cache dependencies
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pip
      /tmp/.uv-cache
    key: ${{ runner.os }}-deps-${{ hashFiles('pyproject.toml') }}
```

## 今後の拡張予定

- [ ] 並列実行サポート
- [ ] カスタム検証ルールの設定ファイル対応
- [ ] より詳細なセキュリティスキャン
- [ ] テンプレート間の依存関係チェック
- [ ] 自動修正機能
- [ ] Web UI での結果表示

## 関連ドキュメント

- [GitHub Actions Simulator ユーザーガイド](actions/USER_GUIDE.md)
- [Docker カスタマイズガイド](DOCKER_CUSTOMIZATION_GUIDE.md)
- [pre-commit 統合ガイド](PRE_COMMIT_INTEGRATION.md)
- [トラブルシューティングガイド](TROUBLESHOOTING.md)

## サポート

問題が発生した場合は、以下の手順で対応してください：

1. [トラブルシューティング](#トラブルシューティング) セクションを確認
2. `make validate-templates --verbose` で詳細ログを確認
3. GitHub Issues で問題を報告
4. 検証レポートを添付して詳細な分析を依頼
