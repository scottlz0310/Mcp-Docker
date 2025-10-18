#!/usr/bin/env python3
"""
GitHub Actions API統合テスト
"""

import os
import pytest
from src.mcp_github_actions.github_api import GitHubActionsAPI, GitHubActionsAPIError


@pytest.mark.integration
def test_github_actions_api():
    """GitHub Actions API の統合テスト"""
    # 環境変数チェック
    if not os.getenv("GITHUB_TOKEN") and not os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"):
        pytest.skip("GITHUB_TOKENが設定されていません")

    try:
        # APIクライアント初期化
        api = GitHubActionsAPI(owner="scottlz0310", repo="Mcp-Docker")
        assert api is not None

        # ワークフロー実行一覧取得
        runs = api.list_workflow_runs(per_page=5)
        assert isinstance(runs, list)

        if runs:
            latest_run = runs[0]
            assert latest_run.id > 0
            assert latest_run.name
            assert latest_run.status

            # ジョブ一覧取得
            jobs = api.list_workflow_jobs(latest_run.id)
            assert isinstance(jobs, list)

    except GitHubActionsAPIError:
        pytest.skip("GitHub APIアクセスエラー")
