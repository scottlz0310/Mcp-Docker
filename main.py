#!/usr/bin/env python3
"""
MCP Docker Environment - Main Entry Point
==========================================

Model Context Protocol（MCP）サーバーのためのメインエントリーポイントです。
複数のサービスを統一されたインターフェースで管理できます。

Modules:
    - GitHub MCP Server: GitHub API連携機能
    - DateTime Validator: 日付検証・自動修正機能
    - GitHub Actions Simulator: ワークフローシミュレーション機能

Example:
    GitHub MCPサーバーを起動::

        $ python main.py github

    DateTime Validatorを起動::

        $ python main.py datetime

    GitHub Actions Simulatorを起動::

        $ python main.py actions simulate .github/workflows/ci.yml

    バージョン情報を表示::

        $ python main.py --version

Attributes:
    __version__ (str): アプリケーションのバージョン番号

"""

import sys
import subprocess

__version__ = "1.3.0"


def main():
    """
    MCP Docker Environment のメインエントリーポイント

    コマンドライン引数に基づいて適切なサービスを起動します。
    サポートされているサービス: github, datetime, actions

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
        print("Available services: github, datetime, actions")
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
    elif service == "actions":
        # GitHub Actions Simulator
        # 追加の引数をそのまま渡す
        args = sys.argv[2:]
        cmd = ["python", "-m", "services.actions.main"] + args
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
