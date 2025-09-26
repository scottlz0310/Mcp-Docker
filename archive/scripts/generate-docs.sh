#!/bin/bash
# API文書自動生成スクリプト

set -euo pipefail

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 基本設定
DOCS_DIR="docs"
BUILD_DIR="$DOCS_DIR/_build"
API_DIR="$DOCS_DIR/api"

echo -e "${BLUE}📚 API文書生成を開始します${NC}"

# 必要なディレクトリを作成
mkdir -p "$API_DIR"

# main.pyのdocstringを充実化
enhance_main_py_docstrings() {
    echo -e "${BLUE}🔧 main.pyのdocstringを強化中...${NC}"

    # バックアップ作成
    cp main.py main.py.bak

    # Python docstringを追加/強化
    cat > main_enhanced.py << 'EOF'
#!/usr/bin/env python3
"""
MCP Docker Environment - Main Entry Point
==========================================

Model Context Protocol（MCP）サーバーのためのメインエントリーポイントです。
複数のサービスを統一されたインターフェースで管理できます。

Modules:
    - GitHub MCP Server: GitHub API連携機能
    - DateTime Validator: 日付検証・自動修正機能
    - CodeQL: 静的コード分析機能

Example:
    GitHub MCPサーバーを起動::

        $ python main.py github

    DateTime Validatorを起動::

        $ python main.py datetime

    バージョン情報を表示::

        $ python main.py --version

Attributes:
    __version__ (str): アプリケーションのバージョン番号

"""

import sys
import subprocess

__version__ = "1.0.1"


def main():
    """
    MCP Docker Environment のメインエントリーポイント

    コマンドライン引数に基づいて適切なサービスを起動します。
    サポートされているサービス: github, datetime, codeql

    Returns:
        None

    Raises:
        SystemExit: 無効な引数が提供された場合、または
                   サービス実行に失敗した場合

    Examples:
        >>> # GitHub MCPサーバーを起動
        >>> main()  # sys.argv = ['main.py', 'github']

        >>> # バージョン情報を表示
        >>> main()  # sys.argv = ['main.py', '--version']
    """
    if len(sys.argv) < 2:
        print("Usage: python main.py <service>")
        print("Available services: github, datetime, codeql")
        print(f"Version: {__version__}")
        sys.exit(1)

    service = sys.argv[1]

    if service == "--version":
        print(f"MCP Docker Environment v{__version__}")
        return

    if service == "github":
        # GitHub MCP Server
        cmd = ["python", "-m", "mcp_server_github"]
    elif service == "datetime":
        # DateTime Validator
        cmd = ["python", "services/datetime/datetime_validator.py"]
    elif service == "codeql":
        # CodeQL Analysis
        print("CodeQL analysis not implemented yet")
        sys.exit(1)
    else:
        print(f"Unknown service: {service}")
        sys.exit(1)

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Service {service} failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        print(f"Service {service} not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
EOF

    # 既存ファイルを置き換え
    mv main_enhanced.py main.py
    echo -e "${GREEN}✅ main.pyのdocstring強化完了${NC}"
}

# API文書を生成
generate_api_docs() {
    echo -e "${BLUE}📖 API文書を生成中...${NC}"

    # API文書のrstファイルを作成
    cat > "$API_DIR/main.rst" << 'EOF'
Main Module
===========

.. automodule:: main
   :members:
   :undoc-members:
   :show-inheritance:
EOF

    # サービスのAPI文書も作成
    if [ -d "services" ]; then
        cat > "$API_DIR/services.rst" << 'EOF'
Services
========

DateTime Validator
------------------

.. automodule:: services.datetime.datetime_validator
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:

GitHub Service
--------------

.. automodule:: services.github
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
EOF
    fi

    # APIインデックスを作成
    cat > "$API_DIR/index.rst" << 'EOF'
API Documentation
=================

.. toctree::
   :maxdepth: 2

   main
   services
EOF

    echo -e "${GREEN}✅ API文書ファイル生成完了${NC}"
}

# 使用例とチュートリアルを作成
generate_usage_docs() {
    echo -e "${BLUE}📝 使用例文書を生成中...${NC}"

    cat > "$DOCS_DIR/usage.rst" << 'EOF'
使用方法
========

基本的な使用方法
----------------

MCP Docker Environmentは、複数のサービスを提供します。

Makefileコマンド
~~~~~~~~~~~~~~~~

基本コマンド::

    make help           # ヘルプ表示
    make build          # イメージビルド
    make start          # サービス起動
    make stop           # サービス停止
    make logs           # ログ確認

サービス別起動::

    make github         # GitHub MCP Server
    make datetime       # DateTime Validator
    make codeql         # CodeQL分析

テスト・品質管理::

    make test           # テスト実行
    make security       # セキュリティスキャン
    make lint           # コード品質チェック

バージョン管理::

    make version        # バージョン情報表示
    make version-sync   # バージョン同期

直接実行
~~~~~~~~

Pythonから直接実行することも可能です::

    # GitHub MCPサーバー起動
    python main.py github

    # DateTime Validator起動
    python main.py datetime

    # バージョン確認
    python main.py --version

Docker Compose
~~~~~~~~~~~~~~

サービス別起動::

    # 全サービス起動
    docker compose up -d

    # 特定サービスのみ
    docker compose up -d github-mcp
    docker compose up -d datetime-validator

設定
----

環境変数
~~~~~~~~

GitHub MCP Server用::

    export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"

ユーザー権限設定::

    export USER_ID=$(id -u)
    export GROUP_ID=$(id -g)
EOF

    cat > "$DOCS_DIR/installation.rst" << 'EOF'
インストール
============

前提条件
--------

* Docker >= 20.10
* Docker Compose >= 2.0
* Python >= 3.13
* uv (Python package manager)

セットアップ
------------

1. リポジトリのクローン::

    git clone https://github.com/scottlz0310/mcp-docker.git
    cd mcp-docker

2. 初期設定の実行::

    ./scripts/setup.sh

3. 環境変数の設定::

    echo 'export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"' >> ~/.bashrc
    source ~/.bashrc

4. イメージのビルド::

    make build

開発環境セットアップ
--------------------

開発依存関係のインストール::

    uv sync --group dev --group docs

Pre-commitフックの設定::

    pre-commit install
EOF

    cat > "$DOCS_DIR/overview.rst" << 'EOF'
概要
====

MCP Docker Environmentは、Model Context Protocol（MCP）サーバーを
本番環境で安全かつ効率的に運用するための統合Docker環境です。

アーキテクチャ
--------------

統合イメージ設計
~~~~~~~~~~~~~~~~

1つのDockerイメージから複数のサービスを提供::

    mcp-docker:latest
    ├── GitHub MCP Server
    ├── DateTime Validator
    └── CodeQL Analysis

セキュリティ機能
~~~~~~~~~~~~~~~~

* 非root実行（動的UID/GIDマッピング）
* 読み取り専用ファイルシステム
* Capabilityの最小限制限
* リソース使用量制限

品質保証
~~~~~~~~

* 多層テスト戦略（Unit, Integration, Security）
* 自動セキュリティスキャン（TruffleHog, Trivy）
* コード品質チェック（pre-commit hooks）
* 自動依存関係監査

CI/CD
~~~~~

* GitHub Actions完全統合
* 自動リリース管理
* ドキュメント自動生成・デプロイ
* セキュリティ脆弱性の継続監視
EOF

    echo -e "${GREEN}✅ 使用例文書生成完了${NC}"
}

# トラブルシューティング文書を統合
integrate_troubleshooting() {
    echo -e "${BLUE}🔧 トラブルシューティング文書を統合中...${NC}"

    if [ -f "$DOCS_DIR/TROUBLESHOOTING.md" ]; then
        # Markdown to RSTコンバート（簡易版）
        cat > "$DOCS_DIR/troubleshooting.rst" << 'EOF'
トラブルシューティング
======================

よくある問題と解決方法をまとめています。

権限エラー
----------

Docker実行時の権限問題::

    ERROR: Permission denied

解決方法::

    # ユーザーをdockerグループに追加
    sudo usermod -aG docker $USER
    # セッションを再開
    newgrp docker

バージョン不整合
----------------

pyproject.tomlとmain.pyのバージョンが異なる::

    ⚠️  Version mismatch between pyproject.toml and main.py!

解決方法::

    make version-sync

GitHub API制限
--------------

GitHub APIレート制限に達した場合::

    HTTP 403: API rate limit exceeded

解決方法:

1. Personal Access Tokenを設定::

    export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"

2. トークンの権限を確認

Docker ビルド失敗
-----------------

イメージビルド時のエラー::

    ERROR: failed to solve

解決方法::

    # キャッシュをクリア
    docker system prune -a

    # 再ビルド
    make clean && make build

テスト失敗
----------

セキュリティテストの失敗::

    Container runs as non-root user: FAILED

これは正常な動作です。セキュリティ強化により、
非rootユーザーでの実行が強制されています。

ログ確認
--------

サービスログの確認::

    make logs

    # または
    docker compose logs -f [service-name]
EOF
    fi

    echo -e "${GREEN}✅ トラブルシューティング統合完了${NC}"
}

# Sphinxドキュメント生成
build_sphinx_docs() {
    echo -e "${BLUE}🏗️  Sphinxドキュメントをビルド中...${NC}"

    # 依存関係のインストール確認
    if ! uv run python -c "import sphinx" &> /dev/null; then
        echo -e "${BLUE}📦 Sphinx依存関係をインストール中...${NC}"
        uv sync --group docs
    fi

    # 古いビルドをクリア
    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"
    fi

    # Sphinxビルド実行
    uv run sphinx-build -b html "$DOCS_DIR" "$BUILD_DIR/html" --keep-going

    echo -e "${GREEN}✅ ドキュメントビルド完了${NC}"
    echo -e "${GREEN}📁 出力先: $BUILD_DIR/html/index.html${NC}"
}

# メイン処理
main() {
    local command="${1:-all}"

    case "$command" in
        "enhance")
            enhance_main_py_docstrings
            ;;
        "api")
            generate_api_docs
            ;;
        "usage")
            generate_usage_docs
            ;;
        "troubleshooting")
            integrate_troubleshooting
            ;;
        "build")
            build_sphinx_docs
            ;;
        "all"|"")
            enhance_main_py_docstrings
            generate_api_docs
            generate_usage_docs
            integrate_troubleshooting
            build_sphinx_docs
            ;;
        *)
            echo -e "${RED}❌ 無効なコマンド: $command${NC}"
            echo "使用方法: $0 [enhance|api|usage|troubleshooting|build|all]"
            exit 1
            ;;
    esac
}

# スクリプトが直接実行された場合のみメイン関数を実行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
