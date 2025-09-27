"""
GitHub Actions Simulator - 診断サービス
システムヘルスチェックとハングアップ問題の診断機能を提供します。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logger import ActionsLogger
from .docker_integration_checker import DockerIntegrationChecker


class DiagnosticStatus(Enum):
    """診断結果のステータス"""
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class DiagnosticResult:
    """診断結果を表すデータクラス"""
    component: str
    status: DiagnosticStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SystemHealthReport:
    """システム全体のヘルスレポート"""
    overall_status: DiagnosticStatus
    results: List[DiagnosticResult]
    summary: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def has_errors(self) -> bool:
        """エラーが存在するかどうか"""
        return any(result.status == DiagnosticStatus.ERROR for result in self.results)

    @property
    def has_warnings(self) -> bool:
        """警告が存在するかどうか"""
        return any(result.status == DiagnosticStatus.WARNING for result in self.results)


class DiagnosticService:
    """システムヘルスチェックと診断機能を提供するサービス"""

    def __init__(self, logger: Optional[ActionsLogger] = None):
        """
        診断サービスを初期化

        Args:
            logger: ログ出力用のロガー
        """
        self.logger = logger or ActionsLogger(verbose=True)
        self._docker_client_available = None
        self._act_binary_path = None
        self._docker_integration_checker = DockerIntegrationChecker(logger=logger)

    def run_comprehensive_health_check(self) -> SystemHealthReport:
        """
        包括的なシステムヘルスチェックを実行

        Returns:
            SystemHealthReport: システム全体の診断結果
        """
        self.logger.info("包括的なシステムヘルスチェックを開始します...")

        results: List[DiagnosticResult] = []

        # Docker接続性チェック
        results.append(self.check_docker_connectivity())

        # actバイナリチェック
        results.append(self.check_act_binary())

        # コンテナ権限チェック
        results.append(self.check_container_permissions())

        # Dockerソケットアクセスチェック
        results.append(self.check_docker_socket_access())

        # コンテナ通信チェック
        results.append(self.check_container_communication())

        # 環境変数チェック
        results.append(self.check_environment_variables())

        # リソース使用量チェック
        results.append(self.check_resource_usage())

        # 全体的なステータスを決定
        overall_status = self._determine_overall_status(results)

        # サマリーを生成
        summary = self._generate_summary(results, overall_status)

        report = SystemHealthReport(
            overall_status=overall_status,
            results=results,
            summary=summary
        )

        self.logger.info(f"システムヘルスチェック完了: {overall_status.value}")
        return report

    def check_docker_connectivity(self) -> DiagnosticResult:
        """
        Docker接続性をチェック

        Returns:
            DiagnosticResult: Docker接続の診断結果
        """
        self.logger.debug("Docker接続性をチェック中...")

        try:
            # Dockerコマンドの存在確認
            docker_path = shutil.which("docker")
            if not docker_path:
                return DiagnosticResult(
                    component="Docker接続性",
                    status=DiagnosticStatus.ERROR,
                    message="Dockerコマンドが見つかりません",
                    recommendations=[
                        "Docker Desktopまたは Docker Engineをインストールしてください",
                        "PATHにDockerコマンドが含まれていることを確認してください"
                    ]
                )

            # Dockerバージョン確認
            version_result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if version_result.returncode != 0:
                return DiagnosticResult(
                    component="Docker接続性",
                    status=DiagnosticStatus.ERROR,
                    message="Dockerコマンドの実行に失敗しました",
                    details={"stderr": version_result.stderr},
                    recommendations=[
                        "Dockerが正しくインストールされているか確認してください",
                        "Docker Desktopが起動しているか確認してください"
                    ]
                )

            # Docker daemon接続確認
            info_result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=15
            )

            if info_result.returncode != 0:
                return DiagnosticResult(
                    component="Docker接続性",
                    status=DiagnosticStatus.ERROR,
                    message="Docker daemonに接続できません",
                    details={"stderr": info_result.stderr},
                    recommendations=[
                        "Docker Desktopを起動してください",
                        "Docker daemonが実行されているか確認してください",
                        "ユーザーがdockerグループに属しているか確認してください"
                    ]
                )

            # 成功時の詳細情報を取得
            docker_version = version_result.stdout.strip()

            return DiagnosticResult(
                component="Docker接続性",
                status=DiagnosticStatus.OK,
                message="Docker接続は正常です",
                details={
                    "version": docker_version,
                    "docker_path": docker_path
                }
            )

        except subprocess.TimeoutExpired:
            return DiagnosticResult(
                component="Docker接続性",
                status=DiagnosticStatus.ERROR,
                message="Dockerコマンドがタイムアウトしました",
                recommendations=[
                    "Docker daemonの応答が遅い可能性があります",
                    "システムリソースを確認してください"
                ]
            )
        except Exception as e:
            return DiagnosticResult(
                component="Docker接続性",
                status=DiagnosticStatus.ERROR,
                message=f"予期しないエラーが発生しました: {str(e)}",
                recommendations=["システム管理者に連絡してください"]
            )

    def check_act_binary(self) -> DiagnosticResult:
        """
        actバイナリの存在と動作をチェック

        Returns:
            DiagnosticResult: actバイナリの診断結果
        """
        self.logger.debug("actバイナリをチェック中...")

        try:
            # actバイナリの検索
            candidates = [
                shutil.which("act"),
                "/home/linuxbrew/.linuxbrew/bin/act",
                "/usr/local/bin/act",
                "/opt/homebrew/bin/act"
            ]

            act_path = None
            for candidate in candidates:
                if candidate and Path(candidate).exists():
                    act_path = candidate
                    break

            if not act_path:
                return DiagnosticResult(
                    component="actバイナリ",
                    status=DiagnosticStatus.ERROR,
                    message="actバイナリが見つかりません",
                    recommendations=[
                        "以下のコマンドでactをインストールしてください:",
                        "curl -fsSL https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash",
                        "または: brew install act"
                    ]
                )

            # actバージョン確認
            version_result = subprocess.run(
                [act_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if version_result.returncode != 0:
                return DiagnosticResult(
                    component="actバイナリ",
                    status=DiagnosticStatus.ERROR,
                    message="actバイナリの実行に失敗しました",
                    details={"stderr": version_result.stderr},
                    recommendations=[
                        "actバイナリが破損している可能性があります",
                        "actを再インストールしてください"
                    ]
                )

            # actの基本機能テスト（--helpコマンド）
            help_result = subprocess.run(
                [act_path, "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if help_result.returncode != 0:
                return DiagnosticResult(
                    component="actバイナリ",
                    status=DiagnosticStatus.WARNING,
                    message="actのヘルプコマンドが失敗しました",
                    details={"stderr": help_result.stderr},
                    recommendations=["actの設定を確認してください"]
                )

            act_version = version_result.stdout.strip()
            self._act_binary_path = act_path

            return DiagnosticResult(
                component="actバイナリ",
                status=DiagnosticStatus.OK,
                message="actバイナリは正常に動作しています",
                details={
                    "version": act_version,
                    "path": act_path
                }
            )

        except subprocess.TimeoutExpired:
            return DiagnosticResult(
                component="actバイナリ",
                status=DiagnosticStatus.ERROR,
                message="actコマンドがタイムアウトしました",
                recommendations=["システムリソースを確認してください"]
            )
        except Exception as e:
            return DiagnosticResult(
                component="actバイナリ",
                status=DiagnosticStatus.ERROR,
                message=f"予期しないエラーが発生しました: {str(e)}",
                recommendations=["システム管理者に連絡してください"]
            )

    def check_container_permissions(self) -> DiagnosticResult:
        """
        コンテナ権限をチェック

        Returns:
            DiagnosticResult: コンテナ権限の診断結果
        """
        self.logger.debug("コンテナ権限をチェック中...")

        try:
            # 現在のユーザー情報を取得
            user_id = os.getuid() if hasattr(os, 'getuid') else None
            group_id = os.getgid() if hasattr(os, 'getgid') else None

            details = {
                "user_id": user_id,
                "group_id": group_id,
                "is_root": user_id == 0 if user_id is not None else False
            }

            # Dockerグループの確認
            try:
                groups_result = subprocess.run(
                    ["groups"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if groups_result.returncode == 0:
                    groups = groups_result.stdout.strip().split()
                    details["groups"] = groups
                    details["in_docker_group"] = "docker" in groups
                else:
                    details["groups"] = []
                    details["in_docker_group"] = False
            except Exception:
                details["groups"] = []
                details["in_docker_group"] = False

            # Docker socket権限の確認
            docker_socket = Path("/var/run/docker.sock")
            if docker_socket.exists():
                stat_info = docker_socket.stat()
                details["docker_socket_exists"] = True
                details["docker_socket_permissions"] = oct(stat_info.st_mode)[-3:]

                # ソケットへの読み書き権限をテスト
                try:
                    with open(docker_socket, 'r'):
                        # ソケットを開けるかテスト（実際には読み込まない）
                        pass
                    details["docker_socket_accessible"] = True
                except PermissionError:
                    details["docker_socket_accessible"] = False
                except Exception:
                    # ソケットファイルなので通常のファイル操作は失敗するが、
                    # 権限があれば別のエラーになる
                    details["docker_socket_accessible"] = True
            else:
                details["docker_socket_exists"] = False
                details["docker_socket_accessible"] = False

            # 権限の問題を判定
            issues = []
            recommendations = []

            if not details.get("docker_socket_exists", False):
                issues.append("Docker socketが見つかりません")
                recommendations.append("Docker daemonが実行されているか確認してください")

            if not details.get("docker_socket_accessible", False):
                issues.append("Docker socketにアクセスできません")
                if not details.get("in_docker_group", False) and not details.get("is_root", False):
                    recommendations.extend([
                        "ユーザーをdockerグループに追加してください: sudo usermod -aG docker $USER",
                        "ログアウト・ログインしてグループ変更を反映してください"
                    ])

            if issues:
                status = DiagnosticStatus.ERROR
                message = "; ".join(issues)
            else:
                status = DiagnosticStatus.OK
                message = "コンテナ権限は正常です"

            return DiagnosticResult(
                component="コンテナ権限",
                status=status,
                message=message,
                details=details,
                recommendations=recommendations
            )

        except Exception as e:
            return DiagnosticResult(
                component="コンテナ権限",
                status=DiagnosticStatus.ERROR,
                message=f"権限チェック中にエラーが発生しました: {str(e)}",
                recommendations=["システム管理者に連絡してください"]
            )

    def check_docker_socket_access(self) -> DiagnosticResult:
        """
        Dockerソケットアクセスをチェック

        Returns:
            DiagnosticResult: Dockerソケットアクセスの診断結果
        """
        self.logger.debug("Dockerソケットアクセスをチェック中...")

        try:
            # Docker APIを使用した接続テスト
            ping_result = subprocess.run(
                ["docker", "system", "info", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=15
            )

            if ping_result.returncode != 0:
                return DiagnosticResult(
                    component="Dockerソケットアクセス",
                    status=DiagnosticStatus.ERROR,
                    message="Docker APIへの接続に失敗しました",
                    details={"stderr": ping_result.stderr},
                    recommendations=[
                        "Docker daemonが実行されているか確認してください",
                        "Docker socketの権限を確認してください"
                    ]
                )

            # システム情報を解析
            try:
                system_info = json.loads(ping_result.stdout)
                details = {
                    "containers_running": system_info.get("ContainersRunning", 0),
                    "containers_total": system_info.get("Containers", 0),
                    "images": system_info.get("Images", 0),
                    "server_version": system_info.get("ServerVersion", "unknown"),
                    "driver": system_info.get("Driver", "unknown")
                }
            except json.JSONDecodeError:
                details = {"raw_output": ping_result.stdout[:500]}

            # Docker Composeネットワークの確認
            network_result = subprocess.run(
                ["docker", "network", "ls", "--filter", "name=mcp-network", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if network_result.returncode == 0:
                try:
                    networks = [json.loads(line) for line in network_result.stdout.strip().split('\n') if line]
                    details["mcp_network_exists"] = len(networks) > 0
                    if networks:
                        details["mcp_network_info"] = networks[0]
                except (json.JSONDecodeError, ValueError):
                    details["mcp_network_exists"] = False
            else:
                details["mcp_network_exists"] = False

            return DiagnosticResult(
                component="Dockerソケットアクセス",
                status=DiagnosticStatus.OK,
                message="Dockerソケットアクセスは正常です",
                details=details
            )

        except subprocess.TimeoutExpired:
            return DiagnosticResult(
                component="Dockerソケットアクセス",
                status=DiagnosticStatus.ERROR,
                message="Docker APIの応答がタイムアウトしました",
                recommendations=[
                    "Docker daemonの負荷が高い可能性があります",
                    "システムリソースを確認してください"
                ]
            )
        except Exception as e:
            return DiagnosticResult(
                component="Dockerソケットアクセス",
                status=DiagnosticStatus.ERROR,
                message=f"予期しないエラーが発生しました: {str(e)}",
                recommendations=["システム管理者に連絡してください"]
            )

    def check_container_communication(self) -> DiagnosticResult:
        """
        コンテナ通信機能をチェック

        Returns:
            DiagnosticResult: コンテナ通信の診断結果
        """
        self.logger.debug("コンテナ通信機能をチェック中...")

        try:
            # 簡単なコンテナ実行テスト
            test_result = subprocess.run(
                ["docker", "run", "--rm", "hello-world"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if test_result.returncode != 0:
                return DiagnosticResult(
                    component="コンテナ通信",
                    status=DiagnosticStatus.ERROR,
                    message="テストコンテナの実行に失敗しました",
                    details={"stderr": test_result.stderr},
                    recommendations=[
                        "Docker daemonが正常に動作しているか確認してください",
                        "ネットワーク接続を確認してください（イメージのダウンロードが必要な場合）"
                    ]
                )

            # ボリュームマウントのテスト
            mount_test_result = subprocess.run(
                ["docker", "run", "--rm", "-v", "/tmp:/test", "alpine:latest", "ls", "/test"],
                capture_output=True,
                text=True,
                timeout=20
            )

            mount_success = mount_test_result.returncode == 0

            details = {
                "hello_world_success": True,
                "volume_mount_success": mount_success,
                "hello_world_output": test_result.stdout[:200]
            }

            if not mount_success:
                details["mount_error"] = mount_test_result.stderr

            # 警告またはOKの判定
            if mount_success:
                status = DiagnosticStatus.OK
                message = "コンテナ通信は正常です"
            else:
                status = DiagnosticStatus.WARNING
                message = "基本的なコンテナ実行は可能ですが、ボリュームマウントに問題があります"
                recommendations = [
                    "ボリュームマウントの権限を確認してください",
                    "SELinuxまたはAppArmorの設定を確認してください"
                ]

            return DiagnosticResult(
                component="コンテナ通信",
                status=status,
                message=message,
                details=details,
                recommendations=recommendations if status == DiagnosticStatus.WARNING else []
            )

        except subprocess.TimeoutExpired:
            return DiagnosticResult(
                component="コンテナ通信",
                status=DiagnosticStatus.ERROR,
                message="コンテナ実行がタイムアウトしました",
                recommendations=[
                    "Docker daemonの応答が遅い可能性があります",
                    "システムリソースを確認してください"
                ]
            )
        except Exception as e:
            return DiagnosticResult(
                component="コンテナ通信",
                status=DiagnosticStatus.ERROR,
                message=f"予期しないエラーが発生しました: {str(e)}",
                recommendations=["システム管理者に連絡してください"]
            )

    def check_environment_variables(self) -> DiagnosticResult:
        """
        重要な環境変数をチェック

        Returns:
            DiagnosticResult: 環境変数の診断結果
        """
        self.logger.debug("環境変数をチェック中...")

        try:
            # 重要な環境変数のリスト
            important_vars = [
                "DOCKER_HOST",
                "DOCKER_CERT_PATH",
                "DOCKER_TLS_VERIFY",
                "ACT_CACHE_DIR",
                "ACTIONS_SIMULATOR_ENGINE",
                "ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS"
            ]

            env_status = {}
            issues = []
            recommendations = []

            for var in important_vars:
                value = os.environ.get(var)
                env_status[var] = value

                # 特定の環境変数の検証
                if var == "DOCKER_HOST" and value:
                    if not value.startswith(("unix://", "tcp://", "ssh://")):
                        issues.append(f"DOCKER_HOSTの形式が不正です: {value}")
                        recommendations.append("DOCKER_HOSTは unix:// または tcp:// で始まる必要があります")

                elif var == "ACT_CACHE_DIR" and value:
                    cache_path = Path(value)
                    if not cache_path.exists():
                        try:
                            cache_path.mkdir(parents=True, exist_ok=True)
                            env_status[f"{var}_created"] = True
                        except Exception as e:
                            issues.append(f"ACT_CACHE_DIRの作成に失敗しました: {e}")
                            recommendations.append("ACT_CACHE_DIRのパスと権限を確認してください")

                elif var == "ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS" and value:
                    try:
                        timeout_val = int(value)
                        if timeout_val <= 0:
                            issues.append("ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDSは正の整数である必要があります")
                            recommendations.append("タイムアウト値を正の整数に設定してください")
                        env_status[f"{var}_parsed"] = timeout_val
                    except ValueError:
                        issues.append("ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDSが数値ではありません")
                        recommendations.append("タイムアウト値を数値で設定してください")

            # PATH環境変数の確認
            docker_in_path = shutil.which("docker") is not None
            act_in_path = shutil.which("act") is not None

            env_status["PATH_has_docker"] = docker_in_path
            env_status["PATH_has_act"] = act_in_path

            if not docker_in_path:
                issues.append("PATHにdockerコマンドが見つかりません")
                recommendations.append("DockerのインストールパスをPATHに追加してください")

            if not act_in_path:
                issues.append("PATHにactコマンドが見つかりません")
                recommendations.append("actのインストールパスをPATHに追加してください")

            # 結果の判定
            if issues:
                status = DiagnosticStatus.WARNING if docker_in_path else DiagnosticStatus.ERROR
                message = f"{len(issues)}個の環境変数の問題が見つかりました"
            else:
                status = DiagnosticStatus.OK
                message = "環境変数は適切に設定されています"

            return DiagnosticResult(
                component="環境変数",
                status=status,
                message=message,
                details=env_status,
                recommendations=recommendations
            )

        except Exception as e:
            return DiagnosticResult(
                component="環境変数",
                status=DiagnosticStatus.ERROR,
                message=f"環境変数チェック中にエラーが発生しました: {str(e)}",
                recommendations=["システム管理者に連絡してください"]
            )

    def check_resource_usage(self) -> DiagnosticResult:
        """
        システムリソース使用量をチェック

        Returns:
            DiagnosticResult: リソース使用量の診断結果
        """
        self.logger.debug("システムリソース使用量をチェック中...")

        try:
            details = {}
            issues = []
            recommendations = []

            # ディスク使用量の確認
            try:
                df_result = subprocess.run(
                    ["df", "-h", "/"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if df_result.returncode == 0:
                    lines = df_result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        fields = lines[1].split()
                        if len(fields) >= 5:
                            details["disk_usage"] = {
                                "total": fields[1],
                                "used": fields[2],
                                "available": fields[3],
                                "use_percent": fields[4]
                            }

                            # 使用率が90%を超えている場合は警告
                            use_percent = int(fields[4].rstrip('%'))
                            if use_percent > 90:
                                issues.append(f"ディスク使用率が高すぎます: {use_percent}%")
                                recommendations.append("ディスク容量を確保してください")
            except Exception:
                details["disk_usage"] = "取得失敗"

            # メモリ使用量の確認
            try:
                free_result = subprocess.run(
                    ["free", "-h"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if free_result.returncode == 0:
                    lines = free_result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        fields = lines[1].split()
                        if len(fields) >= 3:
                            details["memory_usage"] = {
                                "total": fields[1],
                                "used": fields[2],
                                "available": fields[6] if len(fields) > 6 else "不明"
                            }
            except Exception:
                details["memory_usage"] = "取得失敗"

            # Docker関連のリソース使用量
            try:
                docker_system_result = subprocess.run(
                    ["docker", "system", "df"],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                if docker_system_result.returncode == 0:
                    details["docker_disk_usage"] = docker_system_result.stdout
            except Exception:
                details["docker_disk_usage"] = "取得失敗"

            # Docker統合チェッカーによる追加チェック
            try:
                docker_check = self._docker_integration_checker.run_comprehensive_docker_check()
                details["docker_integration_status"] = docker_check["overall_success"]
                details["docker_integration_summary"] = docker_check["summary"]
            except Exception:
                details["docker_integration_status"] = "チェック失敗"

            # 実行中のDockerコンテナ数
            try:
                ps_result = subprocess.run(
                    ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if ps_result.returncode == 0:
                    lines = ps_result.stdout.strip().split('\n')
                    container_count = max(0, len(lines) - 1)  # ヘッダー行を除く
                    details["running_containers"] = container_count

                    if container_count > 10:
                        issues.append(f"実行中のコンテナが多すぎます: {container_count}個")
                        recommendations.append("不要なコンテナを停止してください")
            except Exception:
                details["running_containers"] = "取得失敗"

            # 結果の判定
            if issues:
                status = DiagnosticStatus.WARNING
                message = f"{len(issues)}個のリソース問題が見つかりました"
            else:
                status = DiagnosticStatus.OK
                message = "システムリソースは正常な範囲内です"

            return DiagnosticResult(
                component="リソース使用量",
                status=status,
                message=message,
                details=details,
                recommendations=recommendations
            )

        except Exception as e:
            return DiagnosticResult(
                component="リソース使用量",
                status=DiagnosticStatus.ERROR,
                message=f"リソースチェック中にエラーが発生しました: {str(e)}",
                recommendations=["システム管理者に連絡してください"]
            )

    def _determine_overall_status(self, results: List[DiagnosticResult]) -> DiagnosticStatus:
        """
        個別の診断結果から全体的なステータスを決定

        Args:
            results: 個別の診断結果のリスト

        Returns:
            DiagnosticStatus: 全体的なステータス
        """
        if any(result.status == DiagnosticStatus.ERROR for result in results):
            return DiagnosticStatus.ERROR
        elif any(result.status == DiagnosticStatus.WARNING for result in results):
            return DiagnosticStatus.WARNING
        else:
            return DiagnosticStatus.OK

    def _generate_summary(self, results: List[DiagnosticResult], overall_status: DiagnosticStatus) -> str:
        """
        診断結果のサマリーを生成

        Args:
            results: 個別の診断結果のリスト
            overall_status: 全体的なステータス

        Returns:
            str: サマリーメッセージ
        """
        total_checks = len(results)
        ok_count = sum(1 for r in results if r.status == DiagnosticStatus.OK)
        warning_count = sum(1 for r in results if r.status == DiagnosticStatus.WARNING)
        error_count = sum(1 for r in results if r.status == DiagnosticStatus.ERROR)

        summary_parts = [
            f"全{total_checks}項目の診断を実行しました。",
            f"正常: {ok_count}項目",
            f"警告: {warning_count}項目",
            f"エラー: {error_count}項目"
        ]

        if overall_status == DiagnosticStatus.OK:
            summary_parts.append("システムは正常に動作する準備ができています。")
        elif overall_status == DiagnosticStatus.WARNING:
            summary_parts.append("いくつかの警告がありますが、基本的な動作は可能です。")
        else:
            summary_parts.append("重大な問題が検出されました。修正が必要です。")

        return " ".join(summary_parts)

    def identify_hangup_causes(self, execution_trace: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        ハングアップの潜在的原因を特定

        Args:
            execution_trace: 実行トレース情報（オプション）

        Returns:
            List[str]: 潜在的なハングアップ原因のリスト
        """
        self.logger.debug("ハングアップの潜在的原因を分析中...")

        causes = []

        # システムヘルスチェックの結果を基に原因を推定
        health_report = self.run_comprehensive_health_check()

        for result in health_report.results:
            if result.status == DiagnosticStatus.ERROR:
                if result.component == "Docker接続性":
                    causes.append("Docker daemonとの通信が失敗している可能性があります")
                elif result.component == "actバイナリ":
                    causes.append("actバイナリが正常に動作していない可能性があります")
                elif result.component == "コンテナ権限":
                    causes.append("コンテナ実行権限が不足している可能性があります")
                elif result.component == "Dockerソケットアクセス":
                    causes.append("Dockerソケットへのアクセスが制限されている可能性があります")
                elif result.component == "コンテナ通信":
                    causes.append("コンテナ間の通信に問題がある可能性があります")

        # 実行トレースがある場合の追加分析
        if execution_trace:
            if execution_trace.get("timeout_occurred"):
                causes.append("プロセスがタイムアウトしてハングアップした可能性があります")

            if execution_trace.get("subprocess_stuck"):
                causes.append("サブプロセスの実行でデッドロックが発生した可能性があります")

            if execution_trace.get("output_buffer_full"):
                causes.append("出力バッファが満杯になってハングアップした可能性があります")

        # 一般的なハングアップ原因も追加
        causes.extend([
            "Docker Composeネットワークの設定に問題がある可能性があります",
            "ボリュームマウントの権限設定に問題がある可能性があります",
            "システムリソース（メモリ、CPU、ディスク）が不足している可能性があります",
            "ファイアウォールやセキュリティソフトウェアがDocker通信を阻害している可能性があります"
        ])

        return causes
