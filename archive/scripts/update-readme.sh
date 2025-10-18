#!/bin/bash
# README.mdの動的セクション更新スクリプト

set -euo pipefail

# カラー定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 基本設定
README_FILE="README.md"
TEMP_FILE="${README_FILE}.tmp"

echo -e "${BLUE}📝 README.mdの動的セクション更新を開始${NC}"

# バージョン情報を取得
get_version_info() {
    local pyproject_version
    pyproject_version=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
    echo "$pyproject_version"
}

# Makeコマンドの一覧を生成
generate_make_commands() {
    echo "### 📋 利用可能コマンド"
    echo ""
    echo "\`\`\`bash"
    make help 2>/dev/null | grep -E '^  make ' | head -20
    echo "\`\`\`"
}

# サービス一覧を生成
generate_services_list() {
    echo "### 🚀 提供サービス"
    echo ""

    # docker-compose.ymlからサービスを抽出
    if [ -f "docker-compose.yml" ]; then
        echo "| サービス名 | ポート | 説明 |"
        echo "|-----------|--------|------|"

        # GitHub MCP Server
        if grep -q "github-mcp" docker-compose.yml; then
            echo "| GitHub MCP | 8080 | GitHub API連携のMCPサーバー |"
        fi

        # DateTime Validator
        if grep -q "datetime-validator" docker-compose.yml; then
            echo "| DateTime Validator | - | 日付検証・自動修正サービス |"
        fi

        # CodeQL
        if grep -q "codeql" docker-compose.yml; then
            echo "| CodeQL | - | 静的コード分析ツール |"
        fi
    fi
    echo ""
}

# バージョン情報セクションを生成
generate_version_section() {
    local version
    version=$(get_version_info)

    echo "### 📦 バージョン情報"
    echo ""
    echo "- **現在のバージョン**: v${version}"
    echo "- **最終更新**: $(date '+%Y年%m月%d日')"
    echo "- **サポート**: Python 3.13+"
    echo ""
}

# リポジトリ統計を生成
generate_repo_stats() {
    echo "### 📊 プロジェクト統計"
    echo ""

    # ファイル数
    local file_count
    file_count=$(find . -type f -name "*.py" -o -name "*.yml" -o -name "*.yaml" -o -name "*.sh" | wc -l)
    echo "- **ファイル数**: ${file_count}個のソースファイル"

    # テストファイル数
    local test_count
    test_count=$(find tests -name "*.bats" -o -name "*.py" 2>/dev/null | wc -l)
    echo "- **テスト数**: ${test_count}個のテストファイル"

    # Docker設定
    if [ -f "docker-compose.yml" ]; then
        local service_count
        service_count=$(grep -c "^  [a-zA-Z]" docker-compose.yml || echo "0")
        echo "- **Dockerサービス**: ${service_count}個の定義済みサービス"
    fi

    # 最新コミット
    local latest_commit
    latest_commit=$(git log -1 --oneline 2>/dev/null | head -c 50 || echo "情報なし")
    echo "- **最新コミット**: \`${latest_commit}...\`"
    echo ""
}

# 動的セクションを更新
update_dynamic_sections() {
    # README.mdのバックアップ作成
    cp "$README_FILE" "${README_FILE}.bak"

    # 新しいREADMEを生成
    cat > "$TEMP_FILE" << 'EOF'
# MCP Docker Environment

Model Context Protocol（MCP）サーバーのためのプロダクション対応Docker環境

[![CI Status](https://github.com/scottlz0310/mcp-docker/workflows/CI/badge.svg)](https://github.com/scottlz0310/mcp-docker/actions)
[![Security Scan](https://github.com/scottlz0310/mcp-docker/workflows/Security/badge.svg)](https://github.com/scottlz0310/mcp-docker/actions)
[![Documentation](https://github.com/scottlz0310/mcp-docker/workflows/Documentation/badge.svg)](https://scottlz0310.github.io/mcp-docker)

EOF

    # 動的セクションを追加
    # shellcheck disable=SC2129
    {
        generate_version_section
        generate_repo_stats
    } >> "$TEMP_FILE"

    # 元のREADMEの構成セクション以降をコピー
    echo "## 📁 構成" >> "$TEMP_FILE"
    echo "" >> "$TEMP_FILE"

    # 静的な構成情報
    cat >> "$TEMP_FILE" << 'EOF'
```
mcp-docker/
├── services/           # サービス別設定
│   ├── github/         # GitHub MCP設定
│   ├── datetime/       # 日付検証スクリプト
│   └── codeql/         # CodeQL設定
├── scripts/            # 管理スクリプト
├── docs/              # ドキュメント
├── tests/             # テストスイート
├── Dockerfile          # 統合イメージ
├── docker-compose.yml  # サービス定義
├── Makefile           # 簡単コマンド
└── .env.template      # 環境変数テンプレート
```

## ✨ 特徴

- **統合イメージ**: 1つのDockerイメージで全機能提供
- **サービス分離**: 同じイメージから異なるコマンドで起動
- **軽量運用**: 必要なサービスのみ選択起動
- **セキュリティ強化**: 非root実行、読み取り専用マウント
- **自動化**: CI/CD、リリース管理、テスト完全自動化

EOF

    # サービス一覧を追加
    generate_services_list >> "$TEMP_FILE"

    # 使用方法を追加
    cat >> "$TEMP_FILE" << 'EOF'
## 🚀 クイックスタート

### 1. 初期設定
```bash
# 環境変数設定
echo 'export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc

# セットアップ実行
./scripts/setup.sh
```

### 2. 使用方法

EOF

    # Makeコマンド一覧を追加
    {
        generate_make_commands
    } >> "$TEMP_FILE"

    # バージョン管理の説明を追加
    cat >> "$TEMP_FILE" << 'EOF'

## 📦 バージョン管理

### 現在のバージョンを確認

```bash
make version
```

このコマンドで以下の情報が表示されます：

- pyproject.tomlのバージョン
- main.pyのバージョン
- 最新のGitタグ（存在する場合）
- 推奨される次のバージョン（patch/minor/major）

### バージョンの同期

pyproject.tomlとmain.pyのバージョンが不整合の場合、自動で同期できます：

```bash
make version-sync
```

このコマンドはpyproject.tomlのバージョンをmain.pyに反映します。

### リリース実行

GitHub ActionsのRelease Managementワークフローを使用：

1. GitHubのActionsタブから「🚀 Release Management」を選択
2. 「Run workflow」をクリック
3. バージョン入力欄に新しいバージョンを指定（現在のバージョン情報はワークフロー実行後にSummaryで確認可能）
4. 必要に応じて「Mark as prerelease」をチェック

## 📚 ドキュメント

### ドキュメント生成

```bash
make docs              # ドキュメント生成
make docs-serve        # ローカルでドキュメント表示
make docs-clean        # ドキュメントクリーンアップ
```

### オンラインドキュメント

- **メインドキュメント**: https://scottlz0310.github.io/mcp-docker
- **API リファレンス**: 自動生成されたSphinxドキュメント
- **トラブルシューティング**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

## 🔧 サービス詳細

### GitHub MCP Server

- ポート: 8080
- GitHub API連携
- 環境変数: `GITHUB_PERSONAL_ACCESS_TOKEN`

### DateTime Validator

- ファイル監視による日付自動修正
- 2025-10, 2024-12などの疑わしい日付を検出

### CodeQL

- 静的コード分析
- オンデマンド実行

## 🛡️ セキュリティ

### セキュリティ機能

- **非root実行**: 動的UID/GIDマッピング
- **読み取り専用マウント**: コンテナセキュリティ強化
- **リソース制限**: メモリ・CPU使用量制限
- **自動セキュリティスキャン**: TruffleHog, Trivy統合

### セキュリティテスト

```bash
make security          # セキュリティスキャン実行
make validate-security # セキュリティ設定検証
```

## 🧪 テスト

```bash
make test              # 基本テスト
make test-all          # 全テストスイート
make test-security     # セキュリティテスト
make test-integration  # 統合テスト
```

## 🤝 開発・貢献

### 開発環境セットアップ

```bash
# 開発依存関係インストール
uv sync --group dev --group docs

# Pre-commitフック設定
pre-commit install
```

### 貢献方法

1. リポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

詳細は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。
詳細は [LICENSE](LICENSE) ファイルをご覧ください。
EOF

    # 一時ファイルを正式なREADMEに移動
    mv "$TEMP_FILE" "$README_FILE"
    echo -e "${GREEN}✅ README.md動的更新完了${NC}"
}

# メイン処理
main() {
    update_dynamic_sections
    echo -e "${BLUE}📖 更新されたREADME.mdを確認してください${NC}"
}

# スクリプトが直接実行された場合のみメイン関数を実行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
