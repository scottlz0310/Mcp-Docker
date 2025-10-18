#!/usr/bin/env python3
# type: ignore
"""
GitHub Actions MCP Server のテストスクリプト
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from mcp_github_actions import (  # noqa: E402
    GitHubActionsAPI,
    GitHubActionsAPIError,
)


def test_github_actions_api():
    """GitHub Actions API のテスト"""
    print("=" * 60)
    print("GitHub Actions API テスト")
    print("=" * 60)

    # 環境変数チェック
    if not os.getenv("GITHUB_TOKEN") and not os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"):
        print("❌ GITHUB_TOKEN 環境変数が設定されていません")
        return False

    try:
        # APIクライアント初期化
        print("\n1. APIクライアント初期化...")
        api = GitHubActionsAPI(owner="scottlz0310", repo="Mcp-Docker")
        print("✅ APIクライアント初期化成功")

        # ワークフロー実行一覧取得
        print("\n2. ワークフロー実行一覧取得...")
        runs = api.list_workflow_runs(per_page=5)
        print(f"✅ {len(runs)} 件のワークフロー実行を取得")

        if runs:
            latest_run = runs[0]
            print("\n最新の実行:")
            print(f"  - Run ID: {latest_run.id}")
            print(f"  - Name: {latest_run.name}")
            print(f"  - Status: {latest_run.status}")
            print(f"  - Conclusion: {latest_run.conclusion}")
            print(f"  - Branch: {latest_run.head_branch}")
            print(f"  - Created: {latest_run.created_at}")

            # ジョブ一覧取得
            print(f"\n3. ジョブ一覧取得 (Run ID: {latest_run.id})...")
            jobs = api.list_workflow_jobs(latest_run.id)
            print(f"✅ {len(jobs)} 件のジョブを取得")

            for job in jobs[:3]:  # 最初の3件のみ表示
                print(f"  - {job.name}: {job.status}")

            # ログ取得（完了したワークフローのみ）
            if latest_run.status == "completed":
                print(f"\n4. ログ取得 (Run ID: {latest_run.id})...")
                try:
                    logs = api.get_workflow_run_logs(latest_run.id)
                    print(f"✅ {len(logs)} 件のログファイルを取得")

                    # 最初のログファイルの一部を表示
                    if logs:
                        first_log = list(logs.items())[0]
                        log_name, log_content = first_log
                        print(f"\nログファイル: {log_name}")
                        print(f"サイズ: {len(log_content)} 文字")
                        print("\n最初の10行:")
                        lines = log_content.split("\n")[:10]
                        for line in lines:
                            print(f"  {line}")
                except GitHubActionsAPIError as e:
                    print(f"⚠️  ログ取得エラー: {e}")
            else:
                print(f"\n4. ログ取得スキップ (ステータス: {latest_run.status})")

        print("\n" + "=" * 60)
        print("✅ すべてのテスト成功")
        print("=" * 60)
        return True

    except GitHubActionsAPIError as e:
        print(f"\n❌ GitHub API エラー: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_github_actions_api()
    sys.exit(0 if success else 1)
