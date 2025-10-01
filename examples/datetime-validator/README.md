# DateTime Validator

マークダウンファイル内の日付形式をチェック・検証するツールです。

## 概要

- **用途**: ドキュメントの日付形式統一、古い情報の検出
- **対象**: Markdown ファイル（.md）
- **導入時間**: 約3分

## クイックスタート

### 1. ファイルをコピー

```bash
# 他のプロジェクトで使用する場合
cd ~/your-docs-project
cp -r ~/workspace/Mcp-Docker/examples/datetime-validator ./datetime-check
cd datetime-check
```

### 2. 環境設定

```bash
cp .env.example .env
vim .env
```

`.env` ファイルで以下を設定：

```bash
# 必須: チェック対象ディレクトリ
WATCH_DIRECTORY=./docs

# オプション
LOG_LEVEL=info
CHECK_INTERVAL=60
USER_ID=1000
GROUP_ID=1000
```

### 3. バリデーター実行

```bash
# 継続監視モード
docker compose up -d

# 一回だけ実行
docker compose run --rm datetime-validator python services/datetime/datetime_validator.py --directory /workspace --once
```

## 使用例

### ドキュメントディレクトリの監視

```bash
# docs/ ディレクトリを監視
WATCH_DIRECTORY=./docs docker compose up -d

# 複数ディレクトリを監視（カンマ区切り）
WATCH_DIRECTORY=./docs,./README.md,./CHANGELOG.md docker compose up -d
```

### 特定ファイルの一回限りチェック

```bash
# 特定ファイルをチェック
docker run --rm -v "$PWD:/workspace" \
  ghcr.io/scottlz0310/mcp-docker:latest \
  python services/datetime/datetime_validator.py \
  --file /workspace/README.md \
  --once
```

### 出力結果の確認

```bash
# ログを確認
docker compose logs datetime-validator

# 出力ファイルを確認
ls output/
cat output/datetime_validation_report.json
```

## チェック対象の日付形式

### サポートする形式

| 形式 | 例 | 説明 |
|------|----|----- |
| ISO 8601 | `2025-01-01` | 推奨形式 |
| 日本語形式 | `2025年1月1日` | 日本語ドキュメント |
| US 形式 | `01/01/2025` | アメリカ式 |
| EU 形式 | `01.01.2025` | ヨーロッパ式 |
| 英語形式 | `January 1, 2025` | 英語での表記 |

### 検出する問題

- ❌ 存在しない日付（例: `2025-02-30`）
- ❌ 不正な形式（例: `25/13/2025`）
- ❌ 古すぎる日付（設定可能）
- ❌ 未来すぎる日付（設定可能）
- ⚠️ 形式の不統一
- ⚠️ 更新が必要な可能性がある日付

## 設定オプション

### 環境変数

| 変数名 | 必須 | デフォルト | 説明 |
|--------|------|----------|------|
| `WATCH_DIRECTORY` | ✅ | `./docs` | チェック対象ディレクトリ |
| `CHECK_INTERVAL` | ❌ | `60` | チェック間隔（秒） |
| `LOG_LEVEL` | ❌ | `info` | ログレベル（debug, info, warn, error） |
| `USER_ID` | ❌ | `1000` | 実行ユーザーID |
| `GROUP_ID` | ❌ | `1000` | 実行グループID |

### 高度な設定

カスタム設定ファイル `config.json` を作成：

```json
{
  "date_formats": [
    "%Y-%m-%d",
    "%Y年%m月%d日",
    "%m/%d/%Y"
  ],
  "ignore_patterns": [
    "*.tmp",
    "node_modules/**",
    ".git/**"
  ],
  "validation_rules": {
    "min_year": 2020,
    "max_year": 2030,
    "warn_old_days": 365,
    "require_consistent_format": true
  }
}
```

```bash
# カスタム設定で実行
docker compose run --rm -v "$PWD/config.json:/config.json" \
  datetime-validator python services/datetime/datetime_validator.py \
  --config /config.json --directory /workspace
```

## 出力形式

### JSON レポート

```json
{
  "summary": {
    "total_files": 25,
    "files_with_dates": 18,
    "total_dates": 45,
    "invalid_dates": 2,
    "warnings": 5
  },
  "files": [
    {
      "path": "docs/api.md",
      "dates_found": 3,
      "issues": [
        {
          "line": 15,
          "text": "2025-02-30",
          "type": "invalid_date",
          "message": "存在しない日付です"
        }
      ]
    }
  ]
}
```

### コンソール出力

```
✅ docs/README.md - 3 dates found, all valid
⚠️  docs/api.md - 2 dates found, 1 warning
❌ docs/old.md - 5 dates found, 2 errors

Summary:
- Total files checked: 25
- Files with dates: 18
- Invalid dates: 2
- Warnings: 5
```

## CI/CD での使用

### GitHub Actions

```yaml
name: Documentation Date Check
on: [push, pull_request]

jobs:
  date-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check dates in documentation
        run: |
          docker run --rm -v "$PWD:/workspace" \
            ghcr.io/scottlz0310/mcp-docker:latest \
            python services/datetime/datetime_validator.py \
            --directory /workspace/docs \
            --once \
            --fail-on-error
```

### GitLab CI

```yaml
date-validation:
  image: ghcr.io/scottlz0310/mcp-docker:latest
  script:
    - python services/datetime/datetime_validator.py --directory docs --once --fail-on-error
  only:
    - merge_requests
    - main
```

## トラブルシューティング

### 権限エラー

```bash
# ユーザーIDとグループIDを設定
USER_ID=$(id -u) GROUP_ID=$(id -g) docker compose up -d
```

### ファイルが見つからない

```bash
# マウントパスを確認
docker compose run --rm datetime-validator ls -la /workspace

# 権限を確認
ls -la ./docs
```

### メモリ使用量が多い

```bash
# 大きなファイルを除外
echo "*.pdf
*.zip
*.tar.gz" > .validatorignore

# 設定で除外パターンを指定
```

## 統合例

### pre-commit フック

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: datetime-check
        name: DateTime Validation
        entry: docker run --rm -v "$PWD:/workspace" ghcr.io/scottlz0310/mcp-docker:latest python services/datetime/datetime_validator.py --directory /workspace --once --fail-on-error
        language: system
        files: \\.md$
```

### VSCode 拡張機能

```json
{
  "tasks": [
    {
      "label": "Check Document Dates",
      "type": "shell",
      "command": "docker",
      "args": [
        "run", "--rm", "-v", "${workspaceFolder}:/workspace",
        "ghcr.io/scottlz0310/mcp-docker:latest",
        "python", "services/datetime/datetime_validator.py",
        "--directory", "/workspace", "--once"
      ],
      "group": "test"
    }
  ]
}
```

## アップデート機能

### 自動修正（実験的）

```bash
# 問題のある日付を自動修正
docker compose run --rm datetime-validator \
  python services/datetime/datetime_validator.py \
  --directory /workspace \
  --auto-fix \
  --backup
```

### バックアップ機能

```bash
# 修正前に自動バックアップ
BACKUP_DIR=./backups docker compose run --rm datetime-validator \
  python services/datetime/datetime_validator.py \
  --directory /workspace \
  --auto-fix \
  --backup-dir /output/backups
```
