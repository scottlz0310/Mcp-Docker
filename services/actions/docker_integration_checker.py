"""
GitHub Actions Simulator - Docker統合チェッカー
Dockerソケットアクセスとコンテナ通信を検証する機能を提供します。
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logger import ActionsLogger


class DockerConnectionStatus(Enum):
    """Docker接続ステータス"""
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


@dataclass
class DockerConnectionResult:
    """Docker接続テスト結果"""
    status: DockerConnectionStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    response_time_ms: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ContainerCommunicationResult:
    """コンテナ通信テスト結果"""
    success: bool
    message: str
    container_id: Optional[str] = None
    execution_time_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CompatibilityResult:
    """act-Docker互換性テスト結果"""
    compatible: bool
    message: str
    act_version: Optional[str] = None
    docker_version: Optional[str] = None
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DockerIntegrationChecker:
    """Dockerソケットアクセスとコンテナ通信を検証するクラス"""

    def __init__(self, logger: Optional[ActionsLogger] = None):
        """
        Docker統合チェッカーを初期化

        Args:
            logger: ログ出力用のロガー
        """
        self.logger = logger or ActionsLogger(verbose=True)
        self._docker_socket_path = "/var/run/docker.sock"
        self._retry_count = 3
        self._retry_delay = 2.0

    def verify_socket_access(self) -> bool:
        """
        Dockerソケットへのアクセスを検証

        Returns:
            bool: ソケットアクセスが可能かどうか
        """
        self.logger.debug("Dockerソケットアクセスを検証中...")

        try:
            # ソケットファイルの存在確認
            socket_path = Path(self._docker_socket_path)
            if not socket_path.exists():
                self.logger.error(f"Dockerソケットが見つかりません: {self._docker_socket_path}")
                return False

            # ソケットファイルの権限確認
            stat_info = socket_path.stat()
            self.logger.debug(f"Dockerソケット権限: {oct(stat_info.st_mode)[-3:]}")

            # Docker pingコマンドでソケット通信をテスト
            result = subprocess.run(
                ["docker", "version", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.logger.debug("Dockerソケットアクセス成功")
                return True
            else:
                self.logger.error(f"Dockerソケットアクセス失敗: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("Dockerソケットアクセスがタイムアウトしました")
            return False
        except Exception as e:
            self.logger.error(f"Dockerソケットアクセス検証中にエラー: {str(e)}")
            return False

    def test_container_communication(self) -> ContainerCommunicationResult:
        """
        コンテナ通信をテスト

        Returns:
            ContainerCommunicationResult: 通信テスト結果
        """
        self.logger.debug("コンテナ通信をテスト中...")

        start_time = time.time()

        try:
            # 軽量なテストコンテナを実行
            test_command = [
                "docker", "run", "--rm", "--name", "docker-integration-test",
                "alpine:latest", "echo", "Docker integration test successful"
            ]

            result = subprocess.run(
                test_command,
                capture_output=True,
                text=True,
                timeout=30
            )

            execution_time_ms = (time.time() - start_time) * 1000

            if result.returncode == 0:
                return ContainerCommunicationResult(
                    success=True,
                    message="コンテナ通信テストが成功しました",
                    execution_time_ms=execution_time_ms,
                    details={
                        "stdout": result.stdout.strip(),
                        "command": " ".join(test_command)
                    }
                )
            else:
                return ContainerCommunicationResult(
                    success=False,
                    message="コンテナ通信テストが失敗しました",
                    execution_time_ms=execution_time_ms,
                    details={
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                        "command": " ".join(test_command)
                    }
                )

        except subprocess.TimeoutExpired:
            execution_time_ms = (time.time() - start_time) * 1000
            return ContainerCommunicationResult(
                success=False,
                message="コンテナ通信テストがタイムアウトしました",
                execution_time_ms=execution_time_ms,
                details={"timeout": True}
            )
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return ContainerCommunicationResult(
                success=False,
                message=f"コンテナ通信テスト中にエラーが発生しました: {str(e)}",
                execution_time_ms=execution_time_ms,
                details={"error": str(e)}
            )

    def check_act_docker_compatibility(self) -> CompatibilityResult:
        """
        act-Docker互換性をチェック

        Returns:
            CompatibilityResult: 互換性チェック結果
        """
        self.logger.debug("act-Docker互換性をチェック中...")

        issues = []
        recommendations = []
        act_version = None
        docker_version = None

        try:
            # actバージョンを取得
            act_result = subprocess.run(
                ["act", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if act_result.returncode == 0:
                act_version = act_result.stdout.strip()
                self.logger.debug(f"act バージョン: {act_version}")
            else:
                issues.append("actバイナリが見つからないか、実行できません")
                recommendations.append("actをインストールしてください: brew install act")

            # Dockerバージョンを取得
            docker_result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if docker_result.returncode == 0:
                docker_version = docker_result.stdout.strip()
                self.logger.debug(f"Docker バージョン: {docker_version}")
            else:
                issues.append("Dockerが見つからないか、実行できません")
                recommendations.append("Docker Desktopをインストール・起動してください")

            # actがDockerを認識できるかテスト
            if act_version and docker_version:
                act_list_result = subprocess.run(
                    ["act", "--list"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    cwd="/tmp"  # 安全なディレクトリで実行
                )

                if act_list_result.returncode != 0:
                    # .github/workflowsがない場合のエラーは正常
                    if "no workflows found" not in act_list_result.stderr.lower():
                        issues.append("actがDockerと正常に通信できません")
                        recommendations.append("Docker daemonが実行されているか確認してください")

            # Docker socket マウントの確認
            socket_accessible = self.verify_socket_access()
            if not socket_accessible:
                issues.append("Dockerソケットにアクセスできません")
                recommendations.extend([
                    "ユーザーをdockerグループに追加してください",
                    "Docker daemonが実行されているか確認してください"
                ])

            # 互換性の判定
            compatible = len(issues) == 0

            message = (
                "act-Docker互換性に問題はありません" if compatible
                else f"{len(issues)}個の互換性問題が見つかりました"
            )

            return CompatibilityResult(
                compatible=compatible,
                message=message,
                act_version=act_version,
                docker_version=docker_version,
                issues=issues,
                recommendations=recommendations
            )

        except subprocess.TimeoutExpired:
            return CompatibilityResult(
                compatible=False,
                message="互換性チェックがタイムアウトしました",
                act_version=act_version,
                docker_version=docker_version,
                issues=["コマンド実行がタイムアウトしました"],
                recommendations=["システムリソースを確認してください"]
            )
        except Exception as e:
            return CompatibilityResult(
                compatible=False,
                message=f"互換性チェック中にエラーが発生しました: {str(e)}",
                act_version=act_version,
                docker_version=docker_version,
                issues=[f"予期しないエラー: {str(e)}"],
                recommendations=["システム管理者に連絡してください"]
            )

    def test_docker_daemon_connection_with_retry(self) -> DockerConnectionResult:
        """
        自動リトライ機能付きでDocker daemon接続をテスト

        Returns:
            DockerConnectionResult: 接続テスト結果
        """
        self.logger.debug("Docker daemon接続をリトライ機能付きでテスト中...")

        last_error = None
        total_start_time = time.time()

        for attempt in range(1, self._retry_count + 1):
            self.logger.debug(f"Docker接続試行 {attempt}/{self._retry_count}")

            start_time = time.time()
            try:
                # Docker info コマンドで接続をテスト
                result = subprocess.run(
                    ["docker", "info", "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                response_time_ms = (time.time() - start_time) * 1000

                if result.returncode == 0:
                    # 成功時の詳細情報を取得
                    try:
                        info_data = json.loads(result.stdout)
                        details = {
                            "server_version": info_data.get("ServerVersion", "unknown"),
                            "containers_running": info_data.get("ContainersRunning", 0),
                            "containers_total": info_data.get("Containers", 0),
                            "images": info_data.get("Images", 0),
                            "attempt": attempt,
                            "total_time_ms": (time.time() - total_start_time) * 1000
                        }
                    except json.JSONDecodeError:
                        details = {
                            "attempt": attempt,
                            "raw_output": result.stdout[:200]
                        }

                    return DockerConnectionResult(
                        status=DockerConnectionStatus.CONNECTED,
                        message=f"Docker daemon接続成功 (試行 {attempt}/{self._retry_count})",
                        details=details,
                        response_time_ms=response_time_ms
                    )
                else:
                    last_error = result.stderr
                    self.logger.warning(f"Docker接続試行 {attempt} 失敗: {result.stderr}")

            except subprocess.TimeoutExpired:
                response_time_ms = (time.time() - start_time) * 1000
                last_error = "タイムアウト"
                self.logger.warning(f"Docker接続試行 {attempt} タイムアウト")

                if attempt == self._retry_count:
                    return DockerConnectionResult(
                        status=DockerConnectionStatus.TIMEOUT,
                        message=f"Docker daemon接続がタイムアウトしました ({self._retry_count}回試行)",
                        details={
                            "attempts": self._retry_count,
                            "timeout_seconds": 15,
                            "total_time_ms": (time.time() - total_start_time) * 1000
                        },
                        response_time_ms=response_time_ms
                    )

            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"Docker接続試行 {attempt} エラー: {str(e)}")

            # 最後の試行でない場合は待機
            if attempt < self._retry_count:
                self.logger.debug(f"{self._retry_delay}秒待機してリトライします...")
                time.sleep(self._retry_delay)

        # 全ての試行が失敗した場合
        return DockerConnectionResult(
            status=DockerConnectionStatus.ERROR,
            message=f"Docker daemon接続が失敗しました ({self._retry_count}回試行)",
            details={
                "attempts": self._retry_count,
                "last_error": last_error,
                "total_time_ms": (time.time() - total_start_time) * 1000
            }
        )

    def run_comprehensive_docker_check(self) -> Dict[str, Any]:
        """
        包括的なDocker統合チェックを実行

        Returns:
            Dict[str, Any]: 包括的なチェック結果
        """
        self.logger.info("包括的なDocker統合チェックを開始します...")

        results = {}

        # 1. ソケットアクセス検証
        self.logger.debug("1. Dockerソケットアクセス検証")
        results["socket_access"] = self.verify_socket_access()

        # 2. コンテナ通信テスト
        self.logger.debug("2. コンテナ通信テスト")
        results["container_communication"] = self.test_container_communication()

        # 3. act-Docker互換性チェック
        self.logger.debug("3. act-Docker互換性チェック")
        results["act_compatibility"] = self.check_act_docker_compatibility()

        # 4. Docker daemon接続テスト（リトライ付き）
        self.logger.debug("4. Docker daemon接続テスト")
        results["daemon_connection"] = self.test_docker_daemon_connection_with_retry()

        # 5. 全体的な評価
        overall_success = (
            results["socket_access"] and
            results["container_communication"].success and
            results["act_compatibility"].compatible and
            results["daemon_connection"].status == DockerConnectionStatus.CONNECTED
        )

        results["overall_success"] = overall_success
        results["timestamp"] = datetime.now(timezone.utc).isoformat()

        # サマリーメッセージを生成
        if overall_success:
            results["summary"] = "Docker統合は正常に動作しています"
            self.logger.success("Docker統合チェック完了: 全て正常 ✓")
        else:
            failed_checks = []
            if not results["socket_access"]:
                failed_checks.append("ソケットアクセス")
            if not results["container_communication"].success:
                failed_checks.append("コンテナ通信")
            if not results["act_compatibility"].compatible:
                failed_checks.append("act互換性")
            if results["daemon_connection"].status != DockerConnectionStatus.CONNECTED:
                failed_checks.append("daemon接続")

            results["summary"] = f"Docker統合に問題があります: {', '.join(failed_checks)}"
            self.logger.error(f"Docker統合チェック完了: 問題あり ({', '.join(failed_checks)})")

        return results

    def generate_docker_fix_recommendations(self, check_results: Dict[str, Any]) -> List[str]:
        """
        Docker統合の問題に対する修正推奨事項を生成

        Args:
            check_results: 包括的チェックの結果

        Returns:
            List[str]: 修正推奨事項のリスト
        """
        recommendations = []

        if not check_results.get("socket_access", False):
            recommendations.extend([
                "Dockerソケットアクセスの修正:",
                "  - Docker Desktopを起動してください",
                "  - ユーザーをdockerグループに追加: sudo usermod -aG docker $USER",
                "  - ログアウト・ログインしてグループ変更を反映してください"
            ])

        container_comm = check_results.get("container_communication")
        if container_comm and not container_comm.success:
            recommendations.extend([
                "コンテナ通信の修正:",
                "  - Docker daemonが実行されているか確認してください",
                "  - ネットワーク設定を確認してください",
                "  - ファイアウォール設定を確認してください"
            ])

        act_compat = check_results.get("act_compatibility")
        if act_compat and not act_compat.compatible:
            recommendations.extend([
                "act互換性の修正:",
                *[f"  - {rec}" for rec in act_compat.recommendations]
            ])

        daemon_conn = check_results.get("daemon_connection")
        if daemon_conn and daemon_conn.status != DockerConnectionStatus.CONNECTED:
            recommendations.extend([
                "Docker daemon接続の修正:",
                "  - Docker Desktopを再起動してください",
                "  - システムリソース（メモリ・CPU）を確認してください",
                "  - Docker daemonのログを確認してください"
            ])

        if not recommendations:
            recommendations.append("Docker統合は正常に動作しています。追加の修正は不要です。")

        return recommendations
