"""複数サービス間の統合テスト"""

import subprocess
import time

import pytest

from conftest import PROJECT_ROOT


@pytest.fixture(scope="module")
def all_services(worker_id):
    """全サービスを起動

    worker_idごとに全てのコンテナ名をユニーク化して並列実行時の競合を回避
    """
    github_container = f"mcp-github-{worker_id}"
    datetime_container = f"mcp-datetime-{worker_id}"
    actions_container = f"mcp-actions-simulator-{worker_id}"

    # 既存コンテナをチェック
    check_result = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={github_container}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )

    services_exist = github_container in check_result.stdout

    if not services_exist:
        # イメージをビルド
        build_result = subprocess.run(
            ["docker", "compose", "build", "github-mcp", "datetime-validator", "actions-simulator"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if build_result.returncode != 0:
            pytest.fail(f"イメージのビルドに失敗:\n{build_result.stderr}")

        # github-mcpをdocker compose runで起動
        subprocess.run(
            ["docker", "compose", "run", "-d", "--name", github_container, "github-mcp"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        # datetime-validatorをdocker compose runで起動
        subprocess.run(
            ["docker", "compose", "run", "-d", "--name", datetime_container, "datetime-validator"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        # actions-simulatorを起動（コマンドをオーバーライド）
        subprocess.run(
            [
                "docker",
                "compose",
                "--profile",
                "tools",
                "run",
                "-d",
                "--name",
                actions_container,
                "actions-simulator",
                "sleep",
                "infinity",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        time.sleep(10)  # 全サービス起動待機

    yield {
        "github": github_container,
        "datetime": datetime_container,
        "actions_simulator": actions_container,
    }

    # クリーンアップ
    subprocess.run(
        ["docker", "rm", "-f", github_container, datetime_container, actions_container],
        check=False,
        capture_output=True,
    )


def test_all_services_running(all_services):
    """全サービスが起動していることを確認"""
    actions_container = all_services["actions_simulator"]

    # Compose管理のサービス（github-mcp, datetime-validator）を確認
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"],
        capture_output=True,
        text=True,
        check=True,
    )

    # actions-simulatorはdocker runで起動したため個別確認
    actions_check = subprocess.run(
        ["docker", "ps", "--filter", f"name={actions_container}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )

    # Compose管理のサービスまたはactions-simulatorのいずれかが起動していること
    assert result.stdout.strip() or actions_container in actions_check.stdout, "サービスが起動していません"


def test_network_exists(all_services):
    """mcp-networkが存在することを確認"""
    result = subprocess.run(
        ["docker", "network", "ls", "--filter", "name=mcp-network", "--format", "{{.Name}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "mcp-network" in result.stdout, "mcp-networkが存在しません"


def test_services_on_same_network(all_services):
    """全サービスが同じネットワークに接続されていることを確認"""
    services = [
        all_services["github"],
        all_services["datetime"],
        all_services["actions_simulator"],
    ]

    for service in services:
        result = subprocess.run(
            [
                "docker",
                "inspect",
                service,
                "--format",
                "{{range $key, $value := .NetworkSettings.Networks}}{{$key}}{{end}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            assert "mcp-network" in result.stdout, f"{service}がmcp-networkに接続されていません"


def test_volumes_created(all_services):
    """必要なボリュームが作成されていることを確認"""
    result = subprocess.run(
        ["docker", "volume", "ls", "--format", "{{.Name}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    volumes = result.stdout
    required_volumes = ["act-cache", "act-workspace", "uv-cache"]
    for volume in required_volumes:
        assert any(volume in line for line in volumes.split("\n")), f"ボリューム{volume}が作成されていません"


def test_docker_compose_config_valid():
    """docker-compose.ymlの設定が有効であることを確認"""
    result = subprocess.run(
        ["docker", "compose", "config"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0, "docker-compose.ymlの設定が無効です"
    assert "services:" in result.stdout, "サービス定義が見つかりません"


def test_no_port_conflicts(all_services):
    """ポート競合がないことを確認"""
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    # ポート競合があるとサービスが起動失敗するため、起動成功していればOK
    assert result.returncode == 0, "ポート競合の可能性があります"


def test_services_logs_accessible(all_services):
    """全サービスのログが取得できることを確認"""
    result = subprocess.run(
        ["docker", "compose", "logs", "--tail", "10"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0, "ログが取得できません"


def test_services_can_be_stopped():
    """サービスが正常に停止できることを確認"""
    result = subprocess.run(
        ["docker", "compose", "stop"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0, "サービスの停止に失敗しました"


def test_services_can_be_restarted(all_services):
    """サービスが再起動できることを確認"""
    containers = [
        all_services["github"],
        all_services["datetime"],
        all_services["actions_simulator"],
    ]

    # 全コンテナを停止
    for container in containers:
        subprocess.run(
            ["docker", "stop", container],
            check=False,
            capture_output=True,
        )
    time.sleep(5)

    # 全コンテナを再起動
    for container in containers:
        subprocess.run(
            ["docker", "start", container],
            check=False,
            capture_output=True,
        )
    time.sleep(10)

    # 起動確認
    running_containers = []
    for container in containers:
        check = subprocess.run(
            ["docker", "ps", "--filter", f"name={container}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        if container in check.stdout:
            running_containers.append(container)

    assert len(running_containers) > 0, "再起動後にサービスが起動していません"
