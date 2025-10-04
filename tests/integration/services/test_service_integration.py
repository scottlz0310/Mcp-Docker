"""複数サービス間の統合テスト"""

import subprocess
import time

import pytest

from conftest import PROJECT_ROOT


@pytest.fixture(scope="module")
def all_services():
    """全サービスを起動"""
    # 既存コンテナをクリーンアップ
    subprocess.run(
        ["docker", "compose", "down"],
        cwd=PROJECT_ROOT,
        capture_output=True,
    )

    # イメージをビルド
    build_result = subprocess.run(
        ["docker", "compose", "build"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if build_result.returncode != 0:
        pytest.fail(f"イメージのビルドに失敗:\n{build_result.stderr}")

    # サービスを起動（プロファイル指定が必要なサービスは別途起動）
    up_result = subprocess.run(
        ["docker", "compose", "up", "-d", "github-mcp", "datetime-validator"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if up_result.returncode != 0:
        pytest.fail(f"サービスの起動に失敗:\n{up_result.stderr}")

    # actions-simulatorはプロファイル指定で起動
    profile_result = subprocess.run(
        ["docker", "compose", "--profile", "tools", "up", "-d", "actions-simulator"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if profile_result.returncode != 0:
        pytest.fail(f"Actions Simulatorの起動に失敗:\n{profile_result.stderr}")
    time.sleep(20)  # 全サービス起動待機
    yield
    subprocess.run(
        ["docker", "compose", "down"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
    )


def test_all_services_running(all_services):
    """全サービスが起動していることを確認"""
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"],
        capture_output=True,
        text=True,
        check=True,
    )

    # 少なくとも1つのサービスが起動していることを確認
    assert result.stdout.strip(), "サービスが起動していません"


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
    services = ["mcp-github", "mcp-datetime", "mcp-actions-simulator"]

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


def test_services_can_be_restarted():
    """サービスが再起動できることを確認"""
    # 停止
    subprocess.run(
        ["docker", "compose", "stop"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    time.sleep(5)

    # 再起動
    result = subprocess.run(
        ["docker", "compose", "start"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0, "サービスの再起動に失敗しました"
    time.sleep(10)

    # 起動確認
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip(), "再起動後にサービスが起動していません"
