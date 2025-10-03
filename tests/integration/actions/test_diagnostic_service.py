"""
DiagnosticServiceの単体テスト
"""

from unittest.mock import Mock, patch

from services.actions.diagnostic import (
    DiagnosticService,
    DiagnosticStatus,
    DiagnosticResult,
    SystemHealthReport,
)
from services.actions.logger import ActionsLogger


class TestDiagnosticService:
    """DiagnosticServiceのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.logger = Mock(spec=ActionsLogger)
        self.diagnostic_service = DiagnosticService(logger=self.logger)

    def test_init(self):
        """DiagnosticServiceの初期化テスト"""
        # デフォルトロガーでの初期化
        service = DiagnosticService()
        assert service.logger is not None

        # カスタムロガーでの初期化
        custom_logger = Mock(spec=ActionsLogger)
        service = DiagnosticService(logger=custom_logger)
        assert service.logger == custom_logger

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_check_docker_connectivity_success(self, mock_run, mock_which):
        """Docker接続性チェック成功のテスト"""
        # モックの設定
        mock_which.return_value = "/usr/bin/docker"

        # docker --version の成功レスポンス
        version_result = Mock()
        version_result.returncode = 0
        version_result.stdout = "Docker version 20.10.0"

        # docker info の成功レスポンス
        info_result = Mock()
        info_result.returncode = 0
        info_result.stdout = "Docker info output"

        mock_run.side_effect = [version_result, info_result]

        # テスト実行
        result = self.diagnostic_service.check_docker_connectivity()

        # 結果検証
        assert result.component == "Docker接続性"
        assert result.status == DiagnosticStatus.OK
        assert "Docker接続は正常です" in result.message
        assert "version" in result.details
        assert "docker_path" in result.details

    @patch("shutil.which")
    def test_check_docker_connectivity_not_found(self, mock_which):
        """Dockerコマンドが見つからない場合のテスト"""
        mock_which.return_value = None

        result = self.diagnostic_service.check_docker_connectivity()

        assert result.component == "Docker接続性"
        assert result.status == DiagnosticStatus.ERROR
        assert "Dockerコマンドが見つかりません" in result.message
        assert len(result.recommendations) > 0

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_check_docker_connectivity_daemon_not_running(self, mock_run, mock_which):
        """Docker daemonが実行されていない場合のテスト"""
        mock_which.return_value = "/usr/bin/docker"

        # docker --version は成功
        version_result = Mock()
        version_result.returncode = 0
        version_result.stdout = "Docker version 20.10.0"

        # docker info は失敗（daemon not running）
        info_result = Mock()
        info_result.returncode = 1
        info_result.stderr = "Cannot connect to the Docker daemon"

        mock_run.side_effect = [version_result, info_result]

        result = self.diagnostic_service.check_docker_connectivity()

        assert result.component == "Docker接続性"
        assert result.status == DiagnosticStatus.ERROR
        assert "Docker daemonに接続できません" in result.message

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_check_act_binary_success(self, mock_run, mock_which):
        """actバイナリチェック成功のテスト"""
        mock_which.return_value = "/usr/local/bin/act"

        # act --version の成功レスポンス
        version_result = Mock()
        version_result.returncode = 0
        version_result.stdout = "act version 0.2.81"

        # act --help の成功レスポンス
        help_result = Mock()
        help_result.returncode = 0
        help_result.stdout = "act help output"

        mock_run.side_effect = [version_result, help_result]

        result = self.diagnostic_service.check_act_binary()

        assert result.component == "actバイナリ"
        assert result.status == DiagnosticStatus.OK
        assert "actバイナリは正常に動作しています" in result.message
        assert "version" in result.details
        assert "path" in result.details

    @patch("shutil.which")
    @patch("pathlib.Path.exists")
    def test_check_act_binary_not_found(self, mock_exists, mock_which):
        """actバイナリが見つからない場合のテスト"""
        mock_which.return_value = None
        mock_exists.return_value = False

        result = self.diagnostic_service.check_act_binary()

        assert result.component == "actバイナリ"
        assert result.status == DiagnosticStatus.ERROR
        assert "actバイナリが見つかりません" in result.message
        assert len(result.recommendations) > 0

    @patch("os.getuid")
    @patch("os.getgid")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    def test_check_container_permissions_success(self, mock_stat, mock_exists, mock_run, mock_getgid, mock_getuid):
        """コンテナ権限チェック成功のテスト"""
        # モックの設定
        mock_getuid.return_value = 1000
        mock_getgid.return_value = 1000
        mock_exists.return_value = True

        # groups コマンドの成功レスポンス
        groups_result = Mock()
        groups_result.returncode = 0
        groups_result.stdout = "user docker sudo"
        mock_run.return_value = groups_result

        # Docker socket のstat情報
        stat_info = Mock()
        stat_info.st_mode = 0o660
        mock_stat.return_value = stat_info

        # ファイルオープンのモック（権限あり）
        with patch("builtins.open", mock_open=True):
            result = self.diagnostic_service.check_container_permissions()

        assert result.component == "コンテナ権限"
        assert result.status == DiagnosticStatus.OK
        assert "コンテナ権限は正常です" in result.message

    def test_run_comprehensive_health_check(self):
        """包括的ヘルスチェックのテスト"""
        # 個別チェックメソッドをモック
        with (
            patch.object(self.diagnostic_service, "check_docker_connectivity") as mock_docker,
            patch.object(self.diagnostic_service, "check_act_binary") as mock_act,
            patch.object(self.diagnostic_service, "check_container_permissions") as mock_permissions,
            patch.object(self.diagnostic_service, "check_docker_socket_access") as mock_socket,
            patch.object(self.diagnostic_service, "check_container_communication") as mock_comm,
            patch.object(self.diagnostic_service, "check_environment_variables") as mock_env,
            patch.object(self.diagnostic_service, "check_resource_usage") as mock_resource,
        ):
            # 全て成功の結果を設定
            success_result = DiagnosticResult(component="Test", status=DiagnosticStatus.OK, message="Test success")

            mock_docker.return_value = success_result
            mock_act.return_value = success_result
            mock_permissions.return_value = success_result
            mock_socket.return_value = success_result
            mock_comm.return_value = success_result
            mock_env.return_value = success_result
            mock_resource.return_value = success_result

            # テスト実行
            report = self.diagnostic_service.run_comprehensive_health_check()

            # 結果検証
            assert isinstance(report, SystemHealthReport)
            assert report.overall_status == DiagnosticStatus.OK
            assert len(report.results) == 7
            assert not report.has_errors
            assert not report.has_warnings
            assert "システムは正常に動作する準備ができています" in report.summary

    def test_run_comprehensive_health_check_with_errors(self):
        """エラーがある場合の包括的ヘルスチェックのテスト"""
        with (
            patch.object(self.diagnostic_service, "check_docker_connectivity") as mock_docker,
            patch.object(self.diagnostic_service, "check_act_binary") as mock_act,
            patch.object(self.diagnostic_service, "check_container_permissions") as mock_permissions,
            patch.object(self.diagnostic_service, "check_docker_socket_access") as mock_socket,
            patch.object(self.diagnostic_service, "check_container_communication") as mock_comm,
            patch.object(self.diagnostic_service, "check_environment_variables") as mock_env,
            patch.object(self.diagnostic_service, "check_resource_usage") as mock_resource,
        ):
            # エラー結果を設定
            error_result = DiagnosticResult(component="Test", status=DiagnosticStatus.ERROR, message="Test error")
            success_result = DiagnosticResult(component="Test", status=DiagnosticStatus.OK, message="Test success")

            mock_docker.return_value = error_result  # エラー
            mock_act.return_value = success_result
            mock_permissions.return_value = success_result
            mock_socket.return_value = success_result
            mock_comm.return_value = success_result
            mock_env.return_value = success_result
            mock_resource.return_value = success_result

            # テスト実行
            report = self.diagnostic_service.run_comprehensive_health_check()

            # 結果検証
            assert report.overall_status == DiagnosticStatus.ERROR
            assert report.has_errors
            assert "重大な問題が検出されました" in report.summary

    def test_identify_hangup_causes(self):
        """ハングアップ原因特定のテスト"""
        # run_comprehensive_health_checkをモック
        with patch.object(self.diagnostic_service, "run_comprehensive_health_check") as mock_health_check:
            # 正常な結果を設定
            success_result = DiagnosticResult(component="Test", status=DiagnosticStatus.OK, message="Test success")

            mock_report = SystemHealthReport(
                overall_status=DiagnosticStatus.OK,
                results=[success_result],
                summary="All good",
            )
            mock_health_check.return_value = mock_report

            # テスト実行
            causes = self.diagnostic_service.identify_hangup_causes()

            # 結果検証
            assert isinstance(causes, list)
            assert len(causes) > 0
            assert any("Docker Compose" in cause for cause in causes)

    def test_identify_hangup_causes_with_execution_trace(self):
        """実行トレース付きハングアップ原因特定のテスト"""
        with patch.object(self.diagnostic_service, "run_comprehensive_health_check") as mock_health_check:
            success_result = DiagnosticResult(component="Test", status=DiagnosticStatus.OK, message="Test success")

            mock_report = SystemHealthReport(
                overall_status=DiagnosticStatus.OK,
                results=[success_result],
                summary="All good",
            )
            mock_health_check.return_value = mock_report

            # 実行トレース情報
            execution_trace = {
                "timeout_occurred": True,
                "subprocess_stuck": True,
                "output_buffer_full": False,
            }

            # テスト実行
            causes = self.diagnostic_service.identify_hangup_causes(execution_trace)

            # 結果検証
            assert isinstance(causes, list)
            assert any("タイムアウト" in cause for cause in causes)
            assert any("デッドロック" in cause for cause in causes)


class TestDiagnosticResult:
    """DiagnosticResultのテストクラス"""

    def test_diagnostic_result_creation(self):
        """DiagnosticResultの作成テスト"""
        result = DiagnosticResult(
            component="Test Component",
            status=DiagnosticStatus.OK,
            message="Test message",
            details={"key": "value"},
            recommendations=["recommendation1", "recommendation2"],
        )

        assert result.component == "Test Component"
        assert result.status == DiagnosticStatus.OK
        assert result.message == "Test message"
        assert result.details == {"key": "value"}
        assert result.recommendations == ["recommendation1", "recommendation2"]
        assert result.timestamp is not None


class TestSystemHealthReport:
    """SystemHealthReportのテストクラス"""

    def test_system_health_report_properties(self):
        """SystemHealthReportのプロパティテスト"""
        error_result = DiagnosticResult(
            component="Error Component",
            status=DiagnosticStatus.ERROR,
            message="Error message",
        )
        warning_result = DiagnosticResult(
            component="Warning Component",
            status=DiagnosticStatus.WARNING,
            message="Warning message",
        )
        ok_result = DiagnosticResult(component="OK Component", status=DiagnosticStatus.OK, message="OK message")

        report = SystemHealthReport(
            overall_status=DiagnosticStatus.ERROR,
            results=[error_result, warning_result, ok_result],
            summary="Test summary",
        )

        assert report.has_errors is True
        assert report.has_warnings is True
        assert report.overall_status == DiagnosticStatus.ERROR
        assert len(report.results) == 3

    def test_system_health_report_no_issues(self):
        """問題がない場合のSystemHealthReportテスト"""
        ok_result = DiagnosticResult(component="OK Component", status=DiagnosticStatus.OK, message="OK message")

        report = SystemHealthReport(overall_status=DiagnosticStatus.OK, results=[ok_result], summary="All good")

        assert report.has_errors is False
        assert report.has_warnings is False
