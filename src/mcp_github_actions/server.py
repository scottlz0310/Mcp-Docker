"""
GitHub Actions MCP Server
GitHub REST APIを使用してワークフロー実行ログを取得するMCPサーバー
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)

from .github_api import GitHubActionsAPI, GitHubActionsAPIError

# ロガー設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-github-actions")

# MCPサーバーインスタンス
app = Server("github-actions-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """利用可能なツール一覧を返す"""
    return [
        Tool(
            name="list_workflow_runs",
            description=("リポジトリのワークフロー実行一覧を取得します。最新のワークフロー実行状況を確認できます。"),
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "リポジトリオーナー名",
                    },
                    "repo": {
                        "type": "string",
                        "description": "リポジトリ名",
                    },
                    "workflow_id": {
                        "type": "string",
                        "description": ("ワークフローID (例: ci.yml) - 省略時は全ワークフロー"),
                    },
                    "branch": {
                        "type": "string",
                        "description": "ブランチ名でフィルタ",
                    },
                    "status": {
                        "type": "string",
                        "description": ("ステータスでフィルタ (queued, in_progress, completed)"),
                        "enum": [
                            "queued",
                            "in_progress",
                            "completed",
                        ],
                    },
                    "per_page": {
                        "type": "integer",
                        "description": "取得件数 (デフォルト: 10)",
                        "default": 10,
                    },
                },
                "required": ["owner", "repo"],
            },
        ),
        Tool(
            name="get_workflow_run",
            description="特定のワークフロー実行の詳細情報を取得します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "リポジトリオーナー名",
                    },
                    "repo": {
                        "type": "string",
                        "description": "リポジトリ名",
                    },
                    "run_id": {
                        "type": "integer",
                        "description": "ワークフロー実行ID",
                    },
                },
                "required": ["owner", "repo", "run_id"],
            },
        ),
        Tool(
            name="get_workflow_run_logs",
            description=("ワークフロー実行のログを取得します。各ジョブのログ内容を確認できます。"),
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "リポジトリオーナー名",
                    },
                    "repo": {
                        "type": "string",
                        "description": "リポジトリ名",
                    },
                    "run_id": {
                        "type": "integer",
                        "description": "ワークフロー実行ID",
                    },
                },
                "required": ["owner", "repo", "run_id"],
            },
        ),
        Tool(
            name="list_workflow_jobs",
            description=("ワークフロー実行のジョブ一覧を取得します。各ジョブの実行状況を確認できます。"),
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "リポジトリオーナー名",
                    },
                    "repo": {
                        "type": "string",
                        "description": "リポジトリ名",
                    },
                    "run_id": {
                        "type": "integer",
                        "description": "ワークフロー実行ID",
                    },
                },
                "required": ["owner", "repo", "run_id"],
            },
        ),
        Tool(
            name="get_latest_workflow_logs",
            description=("指定したワークフローの最新実行ログを取得します。最も簡単にログを確認できる方法です。"),
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "リポジトリオーナー名",
                    },
                    "repo": {
                        "type": "string",
                        "description": "リポジトリ名",
                    },
                    "workflow_id": {
                        "type": "string",
                        "description": "ワークフローID (例: ci.yml)",
                    },
                    "branch": {
                        "type": "string",
                        "description": "ブランチ名でフィルタ",
                    },
                },
                "required": ["owner", "repo", "workflow_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> CallToolResult:
    """ツール呼び出しを処理"""
    try:
        # GitHub APIクライアントの初期化
        owner = arguments.get("owner")
        repo = arguments.get("repo")
        api = GitHubActionsAPI(owner=owner, repo=repo)

        if name == "list_workflow_runs":
            runs = api.list_workflow_runs(
                workflow_id=arguments.get("workflow_id"),
                branch=arguments.get("branch"),
                status=arguments.get("status"),
                per_page=arguments.get("per_page", 10),
            )
            result = _format_workflow_runs(runs)
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=result,
                    )
                ]
            )

        elif name == "get_workflow_run":
            run = api.get_workflow_run(arguments["run_id"])
            result = _format_workflow_run(run)
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=result,
                    )
                ]
            )

        elif name == "get_workflow_run_logs":
            logs = api.get_workflow_run_logs(arguments["run_id"])
            result = _format_logs(logs)
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=result,
                    )
                ]
            )

        elif name == "list_workflow_jobs":
            jobs = api.list_workflow_jobs(arguments["run_id"])
            result = _format_jobs(jobs)
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=result,
                    )
                ]
            )

        elif name == "get_latest_workflow_logs":
            workflow_id = arguments["workflow_id"]
            branch = arguments.get("branch")
            latest_run = api.get_latest_workflow_run(workflow_id, branch)
            if not latest_run:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=(f"ワークフロー {workflow_id} の実行が見つかりませんでした。"),
                        )
                    ],
                    isError=True,
                )

            logs = api.get_workflow_run_logs(latest_run.id)
            result = (
                f"# {workflow_id} - 最新実行ログ\n\n"
                f"Run ID: {latest_run.id}\n"
                f"Status: {latest_run.status}\n"
                f"Conclusion: {latest_run.conclusion}\n"
                f"Branch: {latest_run.head_branch}\n"
                f"Created: {latest_run.created_at}\n\n"
                f"{_format_logs(logs)}"
            )
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=result,
                    )
                ]
            )

        else:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Unknown tool: {name}",
                    )
                ],
                isError=True,
            )

    except GitHubActionsAPIError as e:
        logger.error(f"GitHub API Error: {e}")
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"GitHub API エラー: {str(e)}",
                )
            ],
            isError=True,
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"エラーが発生しました: {str(e)}",
                )
            ],
            isError=True,
        )


def _format_workflow_runs(runs: list) -> str:
    """ワークフロー実行一覧をフォーマット"""
    if not runs:
        return "ワークフロー実行が見つかりませんでした。"

    lines = ["# ワークフロー実行一覧\n"]
    for run in runs:
        lines.append(f"## Run #{run.run_number} (ID: {run.id})")
        lines.append(f"- Name: {run.name}")
        lines.append(f"- Status: {run.status}")
        lines.append(f"- Conclusion: {run.conclusion or 'N/A'}")
        lines.append(f"- Branch: {run.head_branch}")
        lines.append(f"- SHA: {run.head_sha[:7]}")
        lines.append(f"- Created: {run.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- URL: {run.html_url}")
        lines.append("")

    return "\n".join(lines)


def _format_workflow_run(run: Any) -> str:
    """ワークフロー実行詳細をフォーマット"""
    return (
        f"# ワークフロー実行詳細\n\n"
        f"Run ID: {run.id}\n"
        f"Name: {run.name}\n"
        f"Status: {run.status}\n"
        f"Conclusion: {run.conclusion or 'N/A'}\n"
        f"Branch: {run.head_branch}\n"
        f"SHA: {run.head_sha}\n"
        f"Run Number: {run.run_number}\n"
        f"Attempt: {run.run_attempt}\n"
        f"Created: {run.created_at}\n"
        f"Updated: {run.updated_at}\n"
        f"URL: {run.html_url}\n"
    )


def _format_jobs(jobs: list) -> str:
    """ジョブ一覧をフォーマット"""
    if not jobs:
        return "ジョブが見つかりませんでした。"

    lines = ["# ジョブ一覧\n"]
    for job in jobs:
        lines.append(f"## {job.name} (ID: {job.id})")
        lines.append(f"- Status: {job.status}")
        lines.append(f"- Conclusion: {job.conclusion or 'N/A'}")
        if job.started_at:
            lines.append(f"- Started: {job.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if job.completed_at:
            lines.append(f"- Completed: {job.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- URL: {job.html_url}")
        lines.append("")

    return "\n".join(lines)


def _format_logs(logs: dict[str, str]) -> str:
    """ログをフォーマット"""
    if not logs:
        return "ログが見つかりませんでした。"

    lines = ["# ワークフローログ\n"]
    for file_name, content in logs.items():
        lines.append(f"## {file_name}\n")
        lines.append("```")
        # ログが長すぎる場合は最後の1000行のみ表示
        log_lines = content.split("\n")
        if len(log_lines) > 1000:
            lines.append(f"... ({len(log_lines) - 1000} 行省略) ...\n")
            lines.extend(log_lines[-1000:])
        else:
            lines.append(content)
        lines.append("```\n")

    return "\n".join(lines)


async def main():
    """サーバーを起動"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
