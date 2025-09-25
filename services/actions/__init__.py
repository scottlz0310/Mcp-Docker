"""
GitHub Actions Simulator Service
===============================

GitHub Actions Simulatorは、GitHub Actions ワークフローをローカル環境で
シミュレーション実行するためのサービスです。

主な機能:
    - ワークフローYAMLの解析と検証
    - ローカル環境でのワークフロー実行
    - ジョブステップの段階的実行
    - 環境変数とシークレットの管理
    - 実行結果とログの出力

使用例:
    python main.py actions simulate .github/workflows/ci.yml
    python main.py actions validate .github/workflows/deploy.yml
    python main.py actions list-jobs .github/workflows/ci.yml

"""

__version__ = "1.0.0"
__author__ = "MCP Docker Team"
