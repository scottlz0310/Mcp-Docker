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

from pathlib import Path

from .path_utils import find_project_root

__version__ = "1.2.0"
__author__ = "MCP Docker Team"

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = find_project_root(PACKAGE_ROOT)
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "config" / "act-runner.toml"
OUTPUT_ROOT = PROJECT_ROOT / "output"
ACTIONS_OUTPUT_DIR = OUTPUT_ROOT / "actions"

__all__ = [
    "DEFAULT_CONFIG_PATH",
    "ACTIONS_OUTPUT_DIR",
    "OUTPUT_ROOT",
    "PROJECT_ROOT",
]
