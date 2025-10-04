"""Actions Simulatorサービス統合テスト"""

import subprocess
import time

import pytest

from conftest import PROJECT_ROOT


@pytest.fixture(scope="module")
def actions_simulator_service(worker_id):
    """Actions Simulatorサービスを起動

    worker_idごとにユニークなコンテナ名を使用して並列実行時の競合を回避
    """
    container_name = f"mcp-actions-simulator-{worker_id}"

    # コンテナが既に存在するかチェック
    check_result = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )

    container_exists = container_name in check_result.stdout

    if not container_exists:
        # 既存コンテナをクリーンアップ（念のため）
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
        )

        # イメージをビルド（キャッシュ有効）
        build_result = subprocess.run(
            ["docker", "compose", "build", "actions-simulator"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if build_result.returncode != 0:
            pytest.fail(f"Actions Simulatorイメージのビルドに失敗:\n{build_result.stderr}")

        # サービスを起動（コマンドをオーバーライドしてコンテナを常駐させる）
        up_result = subprocess.run(
            [
                "docker",
                "compose",
                "--profile",
                "tools",
                "run",
                "-d",
                "--name",
                container_name,
                "actions-simulator",
                "sleep",
                "infinity",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if up_result.returncode != 0:
            pytest.fail(f"Actions Simulatorサービスの起動に失敗:\n{up_result.stderr}")

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

        time.sleep(5)  # 追加の安定化待機

    yield container_name

    # 最後のテストが終わったらクリーンアップ
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        check=False,
        capture_output=True,
    )


def test_actions_simulator_container_exists(actions_simulator_service):
    """Actions Simulatorコンテナが存在することを確認"""
    container_name = actions_simulator_service
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert container_name in result.stdout, "Actions Simulatorコンテナが存在しません"


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
    container_name = actions_simulator_service
    result = subprocess.run(
        [
            "docker",
            "inspect",
            container_name,
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
    container_name = actions_simulator_service
    result = subprocess.run(
        [
            "docker",
            "exec",
            container_name,
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
    container_name = actions_simulator_service
    result = subprocess.run(
        ["docker", "exec", container_name, "which", "act"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "actがインストールされていません"
    assert "/usr/local/bin/act" in result.stdout or "/usr/bin/act" in result.stdout


def test_actions_simulator_python_available(actions_simulator_service):
    """Actions SimulatorコンテナでPythonが利用可能であることを確認"""
    container_name = actions_simulator_service
    result = subprocess.run(
        ["docker", "exec", container_name, "python", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Python 3." in result.stdout, "Python 3が利用できません"


def test_actions_simulator_main_py_exists(actions_simulator_service):
    """Actions Simulatorコンテナにmain.pyが存在することを確認"""
    container_name = actions_simulator_service
    result = subprocess.run(
        ["docker", "exec", container_name, "test", "-f", "/app/main.py"],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, "main.pyが存在しません"


def test_actions_simulator_environment_variables(actions_simulator_service):
    """Actions Simulatorコンテナの環境変数が設定されていることを確認"""
    container_name = actions_simulator_service
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
    required_vars = [
        "DOCKER_HOST",
        "ACT_CACHE_DIR",
        "ACTIONS_SIMULATOR_ENGINE",
    ]
    for var in required_vars:
        assert var in env_vars, f"環境変数{var}が設定されていません"


def test_actions_simulator_network_connection(actions_simulator_service):
    """Actions Simulatorコンテナがmcp-networkに接続されていることを確認"""
    container_name = actions_simulator_service
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


def test_actions_simulator_logs_accessible(actions_simulator_service):
    """Actions Simulatorコンテナのログが取得できることを確認"""
    container_name = actions_simulator_service
    result = subprocess.run(
        ["docker", "logs", container_name, "--tail", "10"],
        capture_output=True,
        text=True,
        check=True,
    )
    # ログが取得できることを確認（空でも可）
    assert result.returncode == 0, "ログが取得できません"
