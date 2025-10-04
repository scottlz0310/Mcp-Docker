"""Actions Simulatorサービス統合テスト"""

import subprocess
import time

import pytest

from conftest import PROJECT_ROOT


@pytest.fixture(scope="module")
def actions_simulator_service():
    """Actions Simulatorサービスを起動"""
    # 既存コンテナをクリーンアップ
    subprocess.run(
        ["docker", "compose", "down", "actions-simulator"],
        cwd=PROJECT_ROOT,
        capture_output=True,
    )

    # イメージをビルド
    build_result = subprocess.run(
        ["docker", "compose", "build", "actions-simulator"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if build_result.returncode != 0:
        pytest.fail(f"Actions Simulatorイメージのビルドに失敗:\n{build_result.stderr}")

    # サービスを起動
    up_result = subprocess.run(
        ["docker", "compose", "up", "-d", "actions-simulator"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if up_result.returncode != 0:
        pytest.fail(f"Actions Simulatorサービスの起動に失敗:\n{up_result.stderr}")

    # コンテナが起動するまで待機（プロファイル指定のため起動しない場合あり）
    for _ in range(30):
        check = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=mcp-actions-simulator", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        if "mcp-actions-simulator" in check.stdout:
            break
        time.sleep(1)

    time.sleep(5)  # 追加の安定化待機
    yield
    subprocess.run(
        ["docker", "compose", "down", "actions-simulator"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
    )


def test_actions_simulator_container_exists(actions_simulator_service):
    """Actions Simulatorコンテナが存在することを確認"""
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", "name=mcp-actions-simulator", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "mcp-actions-simulator" in result.stdout, "Actions Simulatorコンテナが存在しません"


def test_actions_simulator_image_built():
    """Actions Simulatorイメージがビルドされていることを確認"""
    result = subprocess.run(
        ["docker", "images", "--filter", "reference=mcp-docker*", "--format", "{{.Repository}}:{{.Tag}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "mcp-docker" in result.stdout, "Actions Simulatorイメージがビルドされていません"


def test_actions_simulator_volumes_configured(actions_simulator_service):
    """Actions Simulatorコンテナのボリュームが設定されていることを確認"""
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "mcp-actions-simulator",
            "--format",
            "{{range .Mounts}}{{.Destination}} {{end}}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    mounts = result.stdout
    required_mounts = ["/app/.github", "/app/output", "/app/logs", "/var/run/docker.sock"]
    for mount in required_mounts:
        assert mount in mounts, f"{mount}がマウントされていません"


def test_actions_simulator_docker_socket_access(actions_simulator_service):
    """Actions SimulatorコンテナがDockerソケットにアクセスできることを確認"""
    result = subprocess.run(
        [
            "docker",
            "exec",
            "mcp-actions-simulator",
            "test",
            "-S",
            "/var/run/docker.sock",
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, "Dockerソケットにアクセスできません"


def test_actions_simulator_act_installed(actions_simulator_service):
    """Actions Simulatorコンテナにactがインストールされていることを確認"""
    result = subprocess.run(
        ["docker", "exec", "mcp-actions-simulator", "which", "act"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "actがインストールされていません"
    assert "/usr/local/bin/act" in result.stdout or "/usr/bin/act" in result.stdout


def test_actions_simulator_python_available(actions_simulator_service):
    """Actions SimulatorコンテナでPythonが利用可能であることを確認"""
    result = subprocess.run(
        ["docker", "exec", "mcp-actions-simulator", "python", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Python 3." in result.stdout, "Python 3が利用できません"


def test_actions_simulator_main_py_exists(actions_simulator_service):
    """Actions Simulatorコンテナにmain.pyが存在することを確認"""
    result = subprocess.run(
        ["docker", "exec", "mcp-actions-simulator", "test", "-f", "/app/main.py"],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, "main.pyが存在しません"


def test_actions_simulator_environment_variables(actions_simulator_service):
    """Actions Simulatorコンテナの環境変数が設定されていることを確認"""
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "mcp-actions-simulator",
            "--format",
            "{{range .Config.Env}}{{println .}}{{end}}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    env_vars = result.stdout
    required_vars = [
        "DOCKER_HOST",
        "ACT_CACHE_DIR",
        "ACTIONS_SIMULATOR_ENGINE",
    ]
    for var in required_vars:
        assert var in env_vars, f"環境変数{var}が設定されていません"


def test_actions_simulator_network_connection(actions_simulator_service):
    """Actions Simulatorコンテナがmcp-networkに接続されていることを確認"""
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "mcp-actions-simulator",
            "--format",
            "{{range $key, $value := .NetworkSettings.Networks}}{{$key}}{{end}}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "mcp-network" in result.stdout, "mcp-networkに接続されていません"


def test_actions_simulator_logs_accessible(actions_simulator_service):
    """Actions Simulatorコンテナのログが取得できることを確認"""
    result = subprocess.run(
        ["docker", "logs", "mcp-actions-simulator", "--tail", "10"],
        capture_output=True,
        text=True,
        check=True,
    )
    # ログが取得できることを確認（空でも可）
    assert result.returncode == 0, "ログが取得できません"
