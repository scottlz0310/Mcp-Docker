"""GitHub MCP Serverサービス統合テスト"""

import os
import subprocess
import time

import pytest

from conftest import PROJECT_ROOT


@pytest.fixture(scope="module")
def github_mcp_service():
    """GitHub MCPサービスを起動"""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
    project_name = f"mcp-test-{worker_id}"
    container_name = f"mcp-github-{worker_id}"

    env = os.environ.copy()
    env["GITHUB_MCP_CONTAINER_NAME"] = container_name

    subprocess.run(
        ["docker", "compose", "-p", project_name, "down", "github-mcp"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        env=env,
    )

    result = subprocess.run(
        ["docker", "compose", "-p", project_name, "up", "-d", "github-mcp"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        pytest.fail(f"GitHub MCPサービスの起動に失敗:\n{result.stderr}")

    # コンテナが起動するまで待機
    for _ in range(30):
        check = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        if container_name in check.stdout:
            break
        time.sleep(1)
    else:
        pytest.fail(f"GitHub MCPコンテナ({container_name})が30秒以内に起動しませんでした")

    time.sleep(5)
    yield container_name
    subprocess.run(
        ["docker", "compose", "-p", project_name, "down"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        env=env,
    )


def test_github_mcp_container_running(github_mcp_service):
    """GitHub MCPコンテナが起動していることを確認"""
    container_name = github_mcp_service
    result = subprocess.run(
        ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert container_name in result.stdout, f"GitHub MCPコンテナ({container_name})が起動していません"


def test_github_mcp_container_healthy(github_mcp_service):
    """GitHub MCPコンテナが正常に動作していることを確認"""
    container_name = github_mcp_service
    result = subprocess.run(
        ["docker", "inspect", container_name, "--format", "{{.State.Status}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "running", f"GitHub MCPコンテナ({container_name})が実行中ではありません"


def test_github_mcp_environment_variables(github_mcp_service):
    """GitHub MCPコンテナの環境変数が設定されていることを確認"""
    container_name = github_mcp_service
    result = subprocess.run(
        [
            "docker",
            "inspect",
            container_name,
            "--format",
            "{{range .Config.Env}}{{println .}}{{end}}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    env_vars = result.stdout
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" in env_vars, "環境変数が設定されていません"


def test_github_mcp_network_connection(github_mcp_service):
    """GitHub MCPコンテナがmcp-networkに接続されていることを確認"""
    container_name = github_mcp_service
    result = subprocess.run(
        [
            "docker",
            "inspect",
            container_name,
            "--format",
            "{{range $key, $value := .NetworkSettings.Networks}}{{$key}}{{end}}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "mcp-network" in result.stdout, "mcp-networkに接続されていません"


def test_github_mcp_logs_no_errors(github_mcp_service):
    """GitHub MCPコンテナのログにエラーがないことを確認"""
    container_name = github_mcp_service
    result = subprocess.run(
        ["docker", "logs", container_name, "--tail", "50"],
        capture_output=True,
        text=True,
        check=True,
    )
    logs = result.stdout + result.stderr
    critical_errors = ["fatal", "panic", "cannot start"]
    for error in critical_errors:
        assert error.lower() not in logs.lower(), f"ログに致命的エラーが含まれています: {error}"
