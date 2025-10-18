"""
GitHub Actions API クライアント
GitHub REST APIを使用してワークフロー実行ログを取得する
"""

from __future__ import annotations

import os
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel


class WorkflowRun(BaseModel):  # type: ignore[misc]
    """ワークフロー実行情報"""

    id: int
    name: str
    head_branch: str
    head_sha: str
    status: str
    conclusion: str | None = None
    created_at: datetime
    updated_at: datetime
    html_url: str
    run_number: int
    run_attempt: int


class WorkflowJob(BaseModel):  # type: ignore[misc]
    """ワークフロージョブ情報"""

    id: int
    run_id: int
    name: str
    status: str
    conclusion: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    html_url: str


class GitHubActionsAPIError(Exception):
    """GitHub Actions API エラー"""

    pass


class GitHubActionsAPI:
    """GitHub Actions API クライアント"""

    def __init__(
        self,
        token: str | None = None,
        owner: str | None = None,
        repo: str | None = None,
    ):
        """
        初期化

        Args:
            token: GitHub Personal Access Token
                (環境変数 GITHUB_TOKEN から取得可能)
            owner: リポジトリオーナー
            repo: リポジトリ名
        """
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not self.token:
            raise GitHubActionsAPIError("GitHub token が設定されていません。GITHUB_TOKEN 環境変数を設定してください。")

        self.owner = owner
        self.repo = repo

        if not self.owner or not self.repo:
            raise GitHubActionsAPIError("リポジトリ情報が必要です。owner と repo を指定してください。")

        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        """GitHub API リクエスト実行"""
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)

        if response.status_code >= 400:
            error_msg = f"GitHub API エラー: {response.status_code}"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg += f" - {error_data['message']}"
            except Exception:
                pass
            raise GitHubActionsAPIError(error_msg)

        return response

    def list_workflow_runs(
        self,
        workflow_id: str | None = None,
        branch: str | None = None,
        status: str | None = None,
        per_page: int = 10,
    ) -> list[WorkflowRun]:
        """
        ワークフロー実行一覧を取得

        Args:
            workflow_id: ワークフローID (例: "ci.yml")
            branch: ブランチ名
            status: ステータス (queued, in_progress, completed)
            per_page: 取得件数

        Returns:
            ワークフロー実行情報のリスト
        """
        if workflow_id:
            endpoint = f"/repos/{self.owner}/{self.repo}/actions/workflows/{workflow_id}/runs"
        else:
            endpoint = f"/repos/{self.owner}/{self.repo}/actions/runs"

        params: dict[str, Any] = {"per_page": per_page}
        if branch:
            params["branch"] = branch
        if status:
            params["status"] = status

        response = self._request("GET", endpoint, params=params)
        data = response.json()

        return [WorkflowRun(**run) for run in data.get("workflow_runs", [])]

    def get_workflow_run(self, run_id: int) -> WorkflowRun:
        """
        特定のワークフロー実行情報を取得

        Args:
            run_id: ワークフロー実行ID

        Returns:
            ワークフロー実行情報
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}"
        response = self._request("GET", endpoint)
        return WorkflowRun(**response.json())

    def list_workflow_jobs(self, run_id: int) -> list[WorkflowJob]:
        """
        ワークフロー実行のジョブ一覧を取得

        Args:
            run_id: ワークフロー実行ID

        Returns:
            ジョブ情報のリスト
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/jobs"
        response = self._request("GET", endpoint)
        data = response.json()

        return [WorkflowJob(**job) for job in data.get("jobs", [])]

    def get_workflow_run_logs(self, run_id: int, output_dir: Path | None = None) -> dict[str, str]:
        """
        ワークフロー実行のログを取得

        Args:
            run_id: ワークフロー実行ID
            output_dir: ログファイルを保存するディレクトリ

        Returns:
            ジョブ名をキー、ログ内容を値とする辞書
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/logs"
        response = self._request("GET", endpoint)

        # ログはZIPファイルとして返される
        logs: dict[str, str] = {}
        with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
            for file_name in zip_file.namelist():
                with zip_file.open(file_name) as log_file:
                    log_content = log_file.read().decode("utf-8")
                    logs[file_name] = log_content

                    # 出力ディレクトリが指定されている場合は
                    # ファイルに保存
                    if output_dir:
                        output_path = output_dir / file_name
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        output_path.write_text(log_content, encoding="utf-8")

        return logs

    def get_job_logs(self, job_id: int) -> str:
        """
        特定のジョブのログを取得

        Args:
            job_id: ジョブID

        Returns:
            ログ内容
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/actions/jobs/{job_id}/logs"
        response = self._request("GET", endpoint)
        return str(response.text)

    def get_latest_workflow_run(self, workflow_id: str, branch: str | None = None) -> WorkflowRun | None:
        """
        最新のワークフロー実行を取得

        Args:
            workflow_id: ワークフローID (例: "ci.yml")
            branch: ブランチ名

        Returns:
            最新のワークフロー実行情報、見つからない場合はNone
        """
        runs = self.list_workflow_runs(workflow_id=workflow_id, branch=branch, per_page=1)
        return runs[0] if runs else None
