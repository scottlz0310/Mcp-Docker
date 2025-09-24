Mcp-Docker Documentation
========================

Welcome to the Mcp-Docker project documentation!

This project provides a production-ready Docker environment for Model Context Protocol (MCP) servers.

Updated: 2025-09-24 - GitHub Pages integration enabled

Contents:

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   overview
   usage
   troubleshooting
   api/index

概要
----

MCP Docker Environmentは、Model Context Protocolサーバーを本番環境で運用するための
完全統合型Docker環境です。

主な特徴
~~~~~~~~

* **統合イメージ**: 1つのDockerイメージで全機能提供
* **サービス分離**: 同じイメージから異なるコマンドで起動
* **軽量運用**: 必要なサービスのみ選択起動
* **セキュリティ強化**: 非root実行、読み取り専用マウント
* **自動化**: CI/CD、リリース管理、テスト完全自動化

サービス
~~~~~~~~

GitHub MCP Server
    GitHub API連携のためのMCPサーバー

DateTime Validator
    日付表記の自動検証・修正サービス

CodeQL
    静的コード分析ツール

インデックスとテーブル
======================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
