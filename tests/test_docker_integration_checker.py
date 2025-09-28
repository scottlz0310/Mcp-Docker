"""
GitHub Actions Simulator - Docker統合チェッカーのテスト
DockerIntegrationCheckerクラスの機能をテストします。
"""

import pytest
from unittest.mock import Mock, patch
import subprocess
import json

from services.actions.docker_integration_checker import (
    DockerIntegrationChecker,
    DockerConnectionStatus,
    DockerConnectionResult,
    ContainerCommunicationResult,
    CompatibilityResult,
)
from services.actions.logger import ActionsLogger


class TestDockerIntegrationChecker:
    """DockerIntegrationCheckerのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        self.logger = Mock(spec=ActionsLogger)
        self.checker = DockerIntegrationChecker(logger=self.logger)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_verify_socket_access_success(self, mock_exists, mock_run):
        """Dockerソケットアクセス検証の成功ケース"""
        # モックの設定
        mock_exists.return_value = True
        mock_run.return_value = Mock(returncode=0, stderr="")

        # テスト実行
        result = self.checker.verify_socket_access()

        # 検証
        assert result is True
        mock_run.assert_called_once()
        self.logger.debug.assert_called()

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_verify_socket_access_socket_not_found(self, mock_exists, mock_run):
        """Dockerソケットが見つからない場合"""
        # モックの設定
        mock_exists.return_value = False

        # テスト実行
        result = self.checker.verify_socket_access()

        # 検証
        assert result is False
        mock_run.assert_not_called()
        self.logger.error.assert_called()

    @patch("subprocess.run")
    def test_test_container_communication_success(self, mock_run):
        """コンテナ通信テストの成功ケース"""
        # モックの設定
        mock_run.return_value = Mock(
            returncode=0, stdout="Docker integration test successful\n", stderr=""
        )

        # テスト実行
        result = self.checker.test_container_communication()

        # 検証
        assert isinstance(result, ContainerCommunicationResult)
        assert result.success is True
        assert "成功" in result.message
        assert result.execution_time_ms is not None
        assert result.execution_time_ms > 0

    @patch("subprocess.run")
    def test_test_container_communication_failure(self, mock_run):
        """コンテナ通信テストの失敗ケース"""
        # モックの設定
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="docker: Error response from daemon"
        )

        # テスト実行
        result = self.checker.test_container_communication()

        # 検証
        assert isinstance(result, ContainerCommunicationResult)
        assert result.success is False
        assert "失敗" in result.message
        assert "docker: Error response from daemon" in result.details["stderr"]

    @patch("subprocess.run")
    def test_test_container_communication_timeout(self, mock_run):
        """コンテナ通信テストのタイムアウトケース"""
        # モックの設定
        mock_run.side_effect = subprocess.TimeoutExpired("docker", 30)

        # テスト実行
        result = self.checker.test_container_communication()

        # 検証
        assert isinstance(result, ContainerCommunicationResult)
        assert result.success is False
        assert "タイムアウト" in result.message
        assert result.details["timeout"] is True

    @patch("subprocess.run")
    def test_check_act_docker_compatibility_success(self, mock_run):
        """act-Docker互換性チェックの成功ケース"""

        # モックの設定
        def mock_run_side_effect(cmd, **kwargs):
            if "act" in cmd and "--version" in cmd:
                return Mock(returncode=0, stdout="act version 0.2.35\n", stderr="")
            elif "docker" in cmd and "--version" in cmd:
                return Mock(returncode=0, stdout="Docker version 24.0.0\n", stderr="")
            elif "act" in cmd and "--list" in cmd:
                return Mock(returncode=1, stderr="no workflows found", stdout="")
            else:
                return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_run_side_effect

        # verify_socket_accessをモック
        with patch.object(self.checker, "verify_socket_access", return_value=True):
            # テスト実行
            result = self.checker.check_act_docker_compatibility()

        # 検証
        assert isinstance(result, CompatibilityResult)
        assert result.compatible is True
        assert "問題はありません" in result.message
        assert result.act_version is not None
        assert result.docker_version is not None
        assert len(result.issues) == 0

    @patch("subprocess.run")
    def test_check_act_docker_compatibility_act_missing(self, mock_run):
        """actが見つからない場合の互換性チェック"""

        # モックの設定
        def mock_run_side_effect(cmd, **kwargs):
            if "act" in cmd and "--version" in cmd:
                return Mock(returncode=1, stdout="", stderr="command not found")
            elif "docker" in cmd and "--version" in cmd:
                return Mock(returncode=0, stdout="Docker version 24.0.0\n", stderr="")
            else:
                return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_run_side_effect

        # テスト実行
        result = self.checker.check_act_docker_compatibility()

        # 検証
        assert isinstance(result, CompatibilityResult)
        assert result.compatible is False
        assert len(result.issues) > 0
        assert any("act" in issue for issue in result.issues)
        assert any("brew install act" in rec for rec in result.recommendations)

    @patch("subprocess.run")
    def test_test_docker_daemon_connection_with_retry_success(self, mock_run):
        """Docker daemon接続テスト（リトライ付き）の成功ケース"""
        # モックの設定
        docker_info = {
            "ServerVersion": "24.0.0",
            "ContainersRunning": 2,
            "Containers": 5,
            "Images": 10,
        }
        mock_run.return_value = Mock(
            returncode=0, stdout=json.dumps(docker_info), stderr=""
        )

        # テスト実行
        result = self.checker.test_docker_daemon_connection_with_retry()

        # 検証
        assert isinstance(result, DockerConnectionResult)
        assert result.status == DockerConnectionStatus.CONNECTED
        assert "成功" in result.message
        assert result.response_time_ms is not None
        assert result.details["server_version"] == "24.0.0"
        assert result.details["attempt"] == 1

    @patch("subprocess.run")
    def test_test_docker_daemon_connection_with_retry_failure_then_success(
        self, mock_run
    ):
        """Docker daemon接続テスト（最初失敗、後で成功）"""
        # モックの設定
        docker_info = {
            "ServerVersion": "24.0.0",
            "ContainersRunning": 0,
            "Containers": 0,
            "Images": 5,
        }

        call_count = 0

        def mock_run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Mock(returncode=1, stderr="Cannot connect to the Docker daemon")
            else:
                return Mock(returncode=0, stdout=json.dumps(docker_info), stderr="")

        mock_run.side_effect = mock_run_side_effect

        # テスト実行
        result = self.checker.test_docker_daemon_connection_with_retry()

        # 検証
        assert isinstance(result, DockerConnectionResult)
        assert result.status == DockerConnectionStatus.CONNECTED
        assert result.details["attempt"] == 2  # 2回目で成功

    @patch("subprocess.run")
    def test_test_docker_daemon_connection_with_retry_all_fail(self, mock_run):
        """Docker daemon接続テスト（全て失敗）"""
        # モックの設定
        mock_run.return_value = Mock(
            returncode=1, stderr="Cannot connect to the Docker daemon"
        )

        # テスト実行
        result = self.checker.test_docker_daemon_connection_with_retry()

        # 検証
        assert isinstance(result, DockerConnectionResult)
        assert result.status == DockerConnectionStatus.ERROR
        assert "失敗" in result.message
        assert result.details["attempts"] == 3
        assert "Cannot connect to the Docker daemon" in result.details["last_error"]

    @patch("subprocess.run")
    def test_test_docker_daemon_connection_with_retry_timeout(self, mock_run):
        """Docker daemon接続テスト（タイムアウト）"""
        # モックの設定
        mock_run.side_effect = subprocess.TimeoutExpired("docker", 15)

        # テスト実行
        result = self.checker.test_docker_daemon_connection_with_retry()

        # 検証
        assert isinstance(result, DockerConnectionResult)
        assert result.status == DockerConnectionStatus.TIMEOUT
        assert "タイムアウト" in result.message
        assert result.details["timeout_seconds"] == 15

    def test_run_comprehensive_docker_check_all_success(self):
        """包括的Dockerチェック（全て成功）"""
        # モックの設定
        with (
            patch.object(self.checker, "verify_socket_access", return_value=True),
            patch.object(self.checker, "test_container_communication") as mock_comm,
            patch.object(self.checker, "check_act_docker_compatibility") as mock_compat,
            patch.object(
                self.checker, "test_docker_daemon_connection_with_retry"
            ) as mock_daemon,
        ):
            mock_comm.return_value = ContainerCommunicationResult(
                success=True, message="成功"
            )
            mock_compat.return_value = CompatibilityResult(
                compatible=True, message="互換性OK"
            )
            mock_daemon.return_value = DockerConnectionResult(
                status=DockerConnectionStatus.CONNECTED, message="接続成功"
            )

            # テスト実行
            result = self.checker.run_comprehensive_docker_check()

            # 検証
            assert result["overall_success"] is True
            assert "正常に動作" in result["summary"]
            assert result["socket_access"] is True
            assert result["container_communication"].success is True
            assert result["act_compatibility"].compatible is True
            assert (
                result["daemon_connection"].status == DockerConnectionStatus.CONNECTED
            )

    def test_run_comprehensive_docker_check_partial_failure(self):
        """包括的Dockerチェック（部分的失敗）"""
        # モックの設定
        with (
            patch.object(self.checker, "verify_socket_access", return_value=False),
            patch.object(self.checker, "test_container_communication") as mock_comm,
            patch.object(self.checker, "check_act_docker_compatibility") as mock_compat,
            patch.object(
                self.checker, "test_docker_daemon_connection_with_retry"
            ) as mock_daemon,
        ):
            mock_comm.return_value = ContainerCommunicationResult(
                success=True, message="成功"
            )
            mock_compat.return_value = CompatibilityResult(
                compatible=True, message="互換性OK"
            )
            mock_daemon.return_value = DockerConnectionResult(
                status=DockerConnectionStatus.CONNECTED, message="接続成功"
            )

            # テスト実行
            result = self.checker.run_comprehensive_docker_check()

            # 検証
            assert result["overall_success"] is False
            assert "問題があります" in result["summary"]
            assert "ソケットアクセス" in result["summary"]

    def test_generate_docker_fix_recommendations(self):
        """Docker修正推奨事項の生成テスト"""
        # テストデータの準備
        check_results = {
            "socket_access": False,
            "container_communication": ContainerCommunicationResult(
                success=False, message="失敗"
            ),
            "act_compatibility": CompatibilityResult(
                compatible=False,
                message="互換性なし",
                recommendations=["actをインストールしてください"],
            ),
            "daemon_connection": DockerConnectionResult(
                status=DockerConnectionStatus.ERROR, message="接続失敗"
            ),
        }

        # テスト実行
        recommendations = self.checker.generate_docker_fix_recommendations(
            check_results
        )

        # 検証
        assert len(recommendations) > 0
        assert any("Dockerソケットアクセスの修正" in rec for rec in recommendations)
        assert any("コンテナ通信の修正" in rec for rec in recommendations)
        assert any("act互換性の修正" in rec for rec in recommendations)
        assert any("Docker daemon接続の修正" in rec for rec in recommendations)

    def test_generate_docker_fix_recommendations_all_ok(self):
        """全て正常な場合の推奨事項生成"""
        # テストデータの準備
        check_results = {
            "socket_access": True,
            "container_communication": ContainerCommunicationResult(
                success=True, message="成功"
            ),
            "act_compatibility": CompatibilityResult(
                compatible=True, message="互換性OK"
            ),
            "daemon_connection": DockerConnectionResult(
                status=DockerConnectionStatus.CONNECTED, message="接続成功"
            ),
        }

        # テスト実行
        recommendations = self.checker.generate_docker_fix_recommendations(
            check_results
        )

        # 検証
        assert len(recommendations) == 1
        assert "正常に動作しています" in recommendations[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
