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
