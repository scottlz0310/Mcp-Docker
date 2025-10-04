"""DateTime Validatorサービス統合テスト"""

import os
import subprocess
import time

import pytest

from conftest import PROJECT_ROOT


@pytest.fixture(scope="module")
def datetime_validator_service():
    """DateTime Validatorサービスを起動"""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
    project_name = f"mcp-test-{worker_id}"
    container_name = f"mcp-datetime-{worker_id}"

    env = os.environ.copy()
    env["DATETIME_VALIDATOR_CONTAINER_NAME"] = container_name

    subprocess.run(
        ["docker", "compose", "-p", project_name, "down", "datetime-validator"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        env=env,
    )

    result = subprocess.run(
        ["docker", "compose", "-p", project_name, "up", "-d", "datetime-validator"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        pytest.fail(f"DateTime Validatorサービスの起動に失敗:\n{result.stderr}")

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
        pytest.fail(f"DateTime Validatorコンテナ({container_name})が30秒以内に起動しませんでした")

    time.sleep(5)
    yield container_name
    subprocess.run(
        ["docker", "compose", "-p", project_name, "down"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        env=env,
    )


def test_datetime_validator_container_running(datetime_validator_service):
    container_name = datetime_validator_service
    result = subprocess.run(
        ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert container_name in result.stdout


def test_datetime_validator_container_healthy(datetime_validator_service):
    container_name = datetime_validator_service
    result = subprocess.run(
        ["docker", "inspect", container_name, "--format", "{{.State.Status}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "running"


def test_datetime_validator_volumes_mounted(datetime_validator_service):
    container_name = datetime_validator_service
    result = subprocess.run(
        ["docker", "inspect", container_name, "--format", "{{range .Mounts}}{{.Destination}} {{end}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    mounts = result.stdout
    assert "/workspace" in mounts
    assert "/output" in mounts


def test_datetime_validator_user_permissions(datetime_validator_service):
    container_name = datetime_validator_service
    result = subprocess.run(
        ["docker", "inspect", container_name, "--format", "{{.Config.User}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    user = result.stdout.strip()
    assert user != "" and user != "0:0"


def test_datetime_validator_network_connection(datetime_validator_service):
    container_name = datetime_validator_service
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
    assert "mcp-network" in result.stdout


def test_datetime_validator_resource_limits(datetime_validator_service):
    container_name = datetime_validator_service
    result = subprocess.run(
        ["docker", "inspect", container_name, "--format", "{{.HostConfig.Memory}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    memory_limit = int(result.stdout.strip())
    assert memory_limit > 0


def test_datetime_validator_logs_no_critical_errors(datetime_validator_service):
    container_name = datetime_validator_service
    result = subprocess.run(
        ["docker", "logs", container_name, "--tail", "50"],
        capture_output=True,
        text=True,
        check=True,
    )
    logs = result.stdout + result.stderr
    if "traceback" in logs.lower():
        pytest.fail(f"ログに致命的エラーが含まれています:\n{logs}")
