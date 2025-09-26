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
