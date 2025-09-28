"""
GitHub Actions Simulator - 自動復旧メカニズム
Docker再接続、サブプロセス再起動、バッファクリア、コンテナ状態リセット機能を持つ
AutoRecoveryクラスを提供します。
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .docker_integration_checker import DockerIntegrationChecker, DockerConnectionStatus
from .logger import ActionsLogger


class RecoveryType(Enum):
    """復旧の種類"""

    DOCKER_RECONNECTION = "docker_reconnection"
    SUBPROCESS_RESTART = "subprocess_restart"
    BUFFER_CLEAR = "buffer_clear"
    CONTAINER_RESET = "container_reset"
    FALLBACK_MODE = "fallback_mode"


class RecoveryStatus(Enum):
    """復旧ステータス"""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    IN_PROGRESS = "in_progress"


@dataclass
class RecoveryAttempt:
    """復旧試行の記録"""

    recovery_type: RecoveryType
    status: RecoveryStatus
    start_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    success_indicators: List[str] = field(default_factory=list)
    failure_reasons: List[str] = field(default_factory=list)


@dataclass
class RecoverySession:
    """復旧セッション情報"""

    session_id: str
    start_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    end_time: Optional[str] = None
    total_duration_ms: Optional[float] = None
    attempts: List[RecoveryAttempt] = field(default_factory=list)
    overall_success: bool = False
    fallback_mode_activated: bool = False
    recovery_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FallbackExecutionResult:
    """フォールバック実行結果"""

    success: bool
    returncode: int
    stdout: str
    stderr: str
    execution_time_ms: float
    fallback_method: str
    limitations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class AutoRecovery:
    """
    Docker再接続とサブプロセス再起動機能を持つ自動復旧クラス
    バッファクリア、コンテナ状態リセット、フォールバック実行モードを提供します。
    """

    def __init__(
        self,
        logger: Optional[ActionsLogger] = None,
        docker_checker: Optional[DockerIntegrationChecker] = None,
        max_recovery_attempts: int = 3,
        recovery_timeout: float = 60.0,
        docker_reconnect_timeout: float = 30.0,
        subprocess_restart_timeout: float = 15.0,
        enable_fallback_mode: bool = True,
    ):
        """
        AutoRecoveryを初期化

        Args:
            logger: ログ出力用のロガー
            docker_checker: Docker統合チェッカー
            max_recovery_attempts: 最大復旧試行回数
            recovery_timeout: 復旧タイムアウト（秒）
            docker_reconnect_timeout: Docker再接続タイムアウト（秒）
            subprocess_restart_timeout: サブプロセス再起動タイムアウト（秒）
            enable_fallback_mode: フォールバックモードを有効にするかどうか
        """
        self.logger = logger or ActionsLogger(verbose=True)
        self.docker_checker = docker_checker or DockerIntegrationChecker(
            logger=self.logger
        )
        self.max_recovery_attempts = max_recovery_attempts
        self.recovery_timeout = recovery_timeout
        self.docker_reconnect_timeout = docker_reconnect_timeout
        self.subprocess_restart_timeout = subprocess_restart_timeout
        self.enable_fallback_mode = enable_fallback_mode

        # 復旧セッション管理
        self._current_session: Optional[RecoverySession] = None
        self._recovery_history: List[RecoverySession] = []
        self._recovery_lock = threading.Lock()

        # フォールバックモード設定
        self._fallback_methods = [
            "direct_docker_run",
            "simplified_act_execution",
            "dry_run_mode",
        ]

    def attempt_docker_reconnection(self) -> bool:
        """
        Docker再接続を試行

        Returns:
            bool: 再接続が成功したかどうか
        """
        self.logger.info("Docker再接続を試行中...")

        attempt = RecoveryAttempt(
            recovery_type=RecoveryType.DOCKER_RECONNECTION,
            status=RecoveryStatus.IN_PROGRESS,
            message="Docker daemon再接続を開始",
        )

        start_time = time.time()

        try:
            # ステップ1: 現在のDocker接続状態を確認
            self.logger.debug("ステップ1: Docker接続状態確認")
            connection_result = (
                self.docker_checker.test_docker_daemon_connection_with_retry()
            )

            if connection_result.status == DockerConnectionStatus.CONNECTED:
                attempt.status = RecoveryStatus.SUCCESS
                attempt.message = "Docker接続は既に正常です"
                attempt.success_indicators.append("Docker daemon接続確認済み")
                self.logger.info("Docker接続は既に正常です")
                return True

            # ステップ2: Docker daemonの再起動を試行
            self.logger.debug("ステップ2: Docker daemon再起動試行")
            restart_success = self._restart_docker_daemon()

            if restart_success:
                attempt.success_indicators.append("Docker daemon再起動成功")

                # ステップ3: 再接続確認
                self.logger.debug("ステップ3: 再接続確認")
                time.sleep(5)  # Docker daemonの起動を待機

                reconnect_result = (
                    self.docker_checker.test_docker_daemon_connection_with_retry()
                )
                if reconnect_result.status == DockerConnectionStatus.CONNECTED:
                    attempt.status = RecoveryStatus.SUCCESS
                    attempt.message = "Docker再接続成功"
                    attempt.success_indicators.append("再接続確認済み")
                    self.logger.success("Docker再接続が成功しました")
                    return True
                else:
                    attempt.failure_reasons.append("再接続後も接続できません")

            # ステップ4: Docker socket権限の修正を試行
            self.logger.debug("ステップ4: Docker socket権限修正試行")
            socket_fix_success = self._fix_docker_socket_permissions()

            if socket_fix_success:
                attempt.success_indicators.append("Docker socket権限修正")

                # 最終確認
                final_result = (
                    self.docker_checker.test_docker_daemon_connection_with_retry()
                )
                if final_result.status == DockerConnectionStatus.CONNECTED:
                    attempt.status = RecoveryStatus.SUCCESS
                    attempt.message = "Docker socket権限修正により再接続成功"
                    self.logger.success(
                        "Docker socket権限修正により再接続が成功しました"
                    )
                    return True

            # 全ての試行が失敗
            attempt.status = RecoveryStatus.FAILED
            attempt.message = "Docker再接続の全ての試行が失敗しました"
            attempt.failure_reasons.append("daemon再起動とsocket権限修正が失敗")
            self.logger.error("Docker再接続の全ての試行が失敗しました")
            return False

        except Exception as e:
            attempt.status = RecoveryStatus.FAILED
            attempt.error = str(e)
            attempt.message = f"Docker再接続中にエラーが発生しました: {str(e)}"
            self.logger.error(f"Docker再接続中にエラーが発生しました: {str(e)}")
            return False

        finally:
            attempt.end_time = datetime.now(timezone.utc).isoformat()
            attempt.duration_ms = (time.time() - start_time) * 1000
            self._record_recovery_attempt(attempt)

    def restart_hung_subprocess(self, process: subprocess.Popen) -> bool:
        """
        ハングしたサブプロセスを再起動

        Args:
            process: 再起動対象のプロセス

        Returns:
            bool: 再起動が成功したかどうか
        """
        if process is None:
            self.logger.warning("再起動対象のプロセスがNullです")
            return False

        self.logger.info(f"ハングしたサブプロセスを再起動中: PID {process.pid}")

        attempt = RecoveryAttempt(
            recovery_type=RecoveryType.SUBPROCESS_RESTART,
            status=RecoveryStatus.IN_PROGRESS,
            message=f"サブプロセス再起動を開始: PID {process.pid}",
            details={"original_pid": process.pid},
        )

        start_time = time.time()

        try:
            # ステップ1: プロセスの現在状態を確認
            self.logger.debug("ステップ1: プロセス状態確認")
            return_code = process.poll()

            if return_code is not None:
                attempt.status = RecoveryStatus.SKIPPED
                attempt.message = (
                    f"プロセスは既に終了しています: 終了コード {return_code}"
                )
                self.logger.info(
                    f"プロセスは既に終了しています: 終了コード {return_code}"
                )
                return True

            # ステップ2: 穏やかな終了を試行 (SIGTERM)
            self.logger.debug("ステップ2: SIGTERM送信")
            try:
                process.terminate()
                attempt.success_indicators.append("SIGTERM送信完了")

                # 5秒待機して終了を確認
                try:
                    process.wait(timeout=5)
                    attempt.status = RecoveryStatus.SUCCESS
                    attempt.message = "プロセスがSIGTERMで正常終了しました"
                    attempt.success_indicators.append("SIGTERM終了確認")
                    self.logger.info("プロセスがSIGTERMで正常終了しました")
                    return True
                except subprocess.TimeoutExpired:
                    self.logger.debug("SIGTERM後のタイムアウト、強制終了に進みます")

            except ProcessLookupError:
                attempt.status = RecoveryStatus.SUCCESS
                attempt.message = "プロセスは既に終了していました"
                self.logger.info("プロセスは既に終了していました")
                return True

            # ステップ3: プロセスグループ終了を試行
            self.logger.debug("ステップ3: プロセスグループ終了試行")
            try:
                if hasattr(os, "killpg"):
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    attempt.success_indicators.append("プロセスグループSIGTERM送信")
                    time.sleep(2)

                    if process.poll() is None:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        attempt.success_indicators.append("プロセスグループSIGKILL送信")
                        time.sleep(1)

            except (OSError, ProcessLookupError):
                self.logger.debug("プロセスグループ終了に失敗、個別終了に進みます")

            # ステップ4: 強制終了 (SIGKILL)
            if process.poll() is None:
                self.logger.debug("ステップ4: SIGKILL送信")
                try:
                    process.kill()
                    attempt.success_indicators.append("SIGKILL送信完了")

                    # 最終確認
                    try:
                        process.wait(timeout=3)
                        attempt.status = RecoveryStatus.SUCCESS
                        attempt.message = "プロセスがSIGKILLで強制終了しました"
                        attempt.success_indicators.append("SIGKILL終了確認")
                        self.logger.info("プロセスがSIGKILLで強制終了しました")
                        return True
                    except subprocess.TimeoutExpired:
                        attempt.status = RecoveryStatus.FAILED
                        attempt.message = "プロセスの強制終了に失敗しました"
                        attempt.failure_reasons.append("SIGKILL後もプロセスが残存")
                        self.logger.error(
                            "プロセスの強制終了に失敗しました - ゾンビプロセスの可能性"
                        )
                        return False

                except ProcessLookupError:
                    attempt.status = RecoveryStatus.SUCCESS
                    attempt.message = "プロセスは既に終了していました"
                    self.logger.info("プロセスは既に終了していました")
                    return True

            # ここに到達した場合は成功
            attempt.status = RecoveryStatus.SUCCESS
            attempt.message = "サブプロセス再起動が完了しました"
            return True

        except Exception as e:
            attempt.status = RecoveryStatus.FAILED
            attempt.error = str(e)
            attempt.message = f"サブプロセス再起動中にエラーが発生しました: {str(e)}"
            self.logger.error(f"サブプロセス再起動中にエラーが発生しました: {str(e)}")
            return False

        finally:
            attempt.end_time = datetime.now(timezone.utc).isoformat()
            attempt.duration_ms = (time.time() - start_time) * 1000
            self._record_recovery_attempt(attempt)

    def clear_output_buffers(self) -> None:
        """
        出力バッファをクリア
        """
        self.logger.debug("出力バッファクリアを開始...")

        attempt = RecoveryAttempt(
            recovery_type=RecoveryType.BUFFER_CLEAR,
            status=RecoveryStatus.IN_PROGRESS,
            message="出力バッファクリアを開始",
        )

        start_time = time.time()

        try:
            # ステップ1: システムバッファのフラッシュ
            self.logger.debug("ステップ1: システムバッファフラッシュ")
            try:
                import sys

                sys.stdout.flush()
                sys.stderr.flush()
                attempt.success_indicators.append("標準出力・エラーバッファフラッシュ")
            except Exception as e:
                attempt.failure_reasons.append(f"標準バッファフラッシュ失敗: {str(e)}")

            # ステップ2: ファイルシステムバッファの同期
            self.logger.debug("ステップ2: ファイルシステム同期")
            try:
                os.sync()
                attempt.success_indicators.append("ファイルシステム同期完了")
            except Exception as e:
                attempt.failure_reasons.append(f"ファイルシステム同期失敗: {str(e)}")

            # ステップ3: 一時ファイルのクリーンアップ
            self.logger.debug("ステップ3: 一時ファイルクリーンアップ")
            temp_dirs = ["/tmp", "/var/tmp"]
            cleaned_files = 0

            for temp_dir in temp_dirs:
                try:
                    temp_path = Path(temp_dir)
                    if temp_path.exists():
                        # act関連の一時ファイルを検索・削除
                        for pattern in ["act_*", "github_actions_*", "docker_*"]:
                            for temp_file in temp_path.glob(pattern):
                                try:
                                    if temp_file.is_file():
                                        temp_file.unlink()
                                        cleaned_files += 1
                                    elif temp_file.is_dir():
                                        import shutil

                                        shutil.rmtree(temp_file)
                                        cleaned_files += 1
                                except (OSError, PermissionError):
                                    pass  # 削除できないファイルはスキップ

                except Exception as e:
                    self.logger.debug(
                        f"一時ディレクトリ {temp_dir} のクリーンアップ中にエラー: {str(e)}"
                    )

            if cleaned_files > 0:
                attempt.success_indicators.append(f"一時ファイル {cleaned_files}個削除")

            # ステップ4: メモリバッファのクリア（ガベージコレクション）
            self.logger.debug("ステップ4: メモリバッファクリア")
            try:
                import gc

                collected = gc.collect()
                attempt.success_indicators.append(
                    f"ガベージコレクション: {collected}オブジェクト回収"
                )
            except Exception as e:
                attempt.failure_reasons.append(f"ガベージコレクション失敗: {str(e)}")

            # 成功判定
            if len(attempt.success_indicators) > 0:
                attempt.status = RecoveryStatus.SUCCESS
                attempt.message = f"出力バッファクリア完了: {len(attempt.success_indicators)}個の操作成功"
                self.logger.info(
                    f"出力バッファクリアが完了しました: {len(attempt.success_indicators)}個の操作成功"
                )
            else:
                attempt.status = RecoveryStatus.FAILED
                attempt.message = "出力バッファクリアの全ての操作が失敗しました"
                self.logger.warning("出力バッファクリアの全ての操作が失敗しました")

        except Exception as e:
            attempt.status = RecoveryStatus.FAILED
            attempt.error = str(e)
            attempt.message = f"出力バッファクリア中にエラーが発生しました: {str(e)}"
            self.logger.error(f"出力バッファクリア中にエラーが発生しました: {str(e)}")

        finally:
            attempt.end_time = datetime.now(timezone.utc).isoformat()
            attempt.duration_ms = (time.time() - start_time) * 1000
            self._record_recovery_attempt(attempt)

    def reset_container_state(self) -> bool:
        """
        コンテナ状態をリセット

        Returns:
            bool: リセットが成功したかどうか
        """
        self.logger.info("コンテナ状態リセットを開始...")

        attempt = RecoveryAttempt(
            recovery_type=RecoveryType.CONTAINER_RESET,
            status=RecoveryStatus.IN_PROGRESS,
            message="コンテナ状態リセットを開始",
        )

        start_time = time.time()

        try:
            # ステップ1: 実行中のactコンテナを特定・停止
            self.logger.debug("ステップ1: actコンテナの特定・停止")
            stopped_containers = self._stop_act_containers()
            if stopped_containers > 0:
                attempt.success_indicators.append(
                    f"actコンテナ {stopped_containers}個停止"
                )

            # ステップ2: 孤立したコンテナの削除
            self.logger.debug("ステップ2: 孤立コンテナの削除")
            removed_containers = self._remove_orphaned_containers()
            if removed_containers > 0:
                attempt.success_indicators.append(
                    f"孤立コンテナ {removed_containers}個削除"
                )

            # ステップ3: 未使用ネットワークの削除
            self.logger.debug("ステップ3: 未使用ネットワークの削除")
            removed_networks = self._cleanup_unused_networks()
            if removed_networks > 0:
                attempt.success_indicators.append(
                    f"未使用ネットワーク {removed_networks}個削除"
                )

            # ステップ4: 未使用ボリュームの削除
            self.logger.debug("ステップ4: 未使用ボリュームの削除")
            removed_volumes = self._cleanup_unused_volumes()
            if removed_volumes > 0:
                attempt.success_indicators.append(
                    f"未使用ボリューム {removed_volumes}個削除"
                )

            # ステップ5: Docker system prune
            self.logger.debug("ステップ5: Docker system prune実行")
            prune_success = self._run_docker_system_prune()
            if prune_success:
                attempt.success_indicators.append("Docker system prune完了")

            # 成功判定
            if len(attempt.success_indicators) > 0:
                attempt.status = RecoveryStatus.SUCCESS
                attempt.message = f"コンテナ状態リセット完了: {len(attempt.success_indicators)}個の操作成功"
                self.logger.success(
                    f"コンテナ状態リセットが完了しました: {len(attempt.success_indicators)}個の操作成功"
                )
                return True
            else:
                attempt.status = RecoveryStatus.PARTIAL
                attempt.message = "コンテナ状態リセットは部分的に成功しました"
                self.logger.warning("コンテナ状態リセットは部分的に成功しました")
                return False

        except Exception as e:
            attempt.status = RecoveryStatus.FAILED
            attempt.error = str(e)
            attempt.message = f"コンテナ状態リセット中にエラーが発生しました: {str(e)}"
            self.logger.error(f"コンテナ状態リセット中にエラーが発生しました: {str(e)}")
            return False

        finally:
            attempt.end_time = datetime.now(timezone.utc).isoformat()
            attempt.duration_ms = (time.time() - start_time) * 1000
            self._record_recovery_attempt(attempt)

    def execute_fallback_mode(
        self, workflow_file: Path, original_command: List[str]
    ) -> FallbackExecutionResult:
        """
        プライマリ実行パスが失敗した場合のフォールバック実行モード

        Args:
            workflow_file: ワークフローファイル
            original_command: 元のコマンド

        Returns:
            FallbackExecutionResult: フォールバック実行結果
        """
        if not self.enable_fallback_mode:
            return FallbackExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr="フォールバックモードが無効です",
                execution_time_ms=0,
                fallback_method="disabled",
                limitations=["フォールバックモードが無効化されています"],
            )

        self.logger.info("フォールバック実行モードを開始...")

        attempt = RecoveryAttempt(
            recovery_type=RecoveryType.FALLBACK_MODE,
            status=RecoveryStatus.IN_PROGRESS,
            message="フォールバック実行モードを開始",
            details={
                "workflow_file": str(workflow_file),
                "original_command": original_command,
            },
        )

        start_time = time.time()

        try:
            # フォールバック方法を順番に試行
            for method in self._fallback_methods:
                self.logger.debug(f"フォールバック方法を試行: {method}")

                try:
                    if method == "direct_docker_run":
                        result = self._fallback_direct_docker_run(workflow_file)
                    elif method == "simplified_act_execution":
                        result = self._fallback_simplified_act_execution(workflow_file)
                    elif method == "dry_run_mode":
                        result = self._fallback_dry_run_mode(workflow_file)
                    else:
                        continue

                    if result.success:
                        attempt.status = RecoveryStatus.SUCCESS
                        attempt.message = f"フォールバック実行成功: {method}"
                        attempt.success_indicators.append(f"成功方法: {method}")
                        self.logger.success(
                            f"フォールバック実行が成功しました: {method}"
                        )
                        return result

                except Exception as e:
                    self.logger.debug(f"フォールバック方法 {method} でエラー: {str(e)}")
                    attempt.failure_reasons.append(f"{method}: {str(e)}")

            # 全てのフォールバック方法が失敗
            attempt.status = RecoveryStatus.FAILED
            attempt.message = "全てのフォールバック方法が失敗しました"
            self.logger.error("全てのフォールバック方法が失敗しました")

            return FallbackExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr="全てのフォールバック方法が失敗しました",
                execution_time_ms=(time.time() - start_time) * 1000,
                fallback_method="all_failed",
                limitations=["プライマリとフォールバック実行の両方が失敗"],
            )

        except Exception as e:
            attempt.status = RecoveryStatus.FAILED
            attempt.error = str(e)
            attempt.message = f"フォールバック実行中にエラーが発生しました: {str(e)}"
            self.logger.error(f"フォールバック実行中にエラーが発生しました: {str(e)}")

            return FallbackExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"フォールバック実行エラー: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
                fallback_method="error",
                limitations=[f"実行エラー: {str(e)}"],
            )

        finally:
            attempt.end_time = datetime.now(timezone.utc).isoformat()
            attempt.duration_ms = (time.time() - start_time) * 1000
            self._record_recovery_attempt(attempt)

    def run_comprehensive_recovery(
        self,
        failed_process: Optional[subprocess.Popen] = None,
        workflow_file: Optional[Path] = None,
        original_command: Optional[List[str]] = None,
    ) -> RecoverySession:
        """
        包括的な復旧処理を実行

        Args:
            failed_process: 失敗したプロセス
            workflow_file: ワークフローファイル
            original_command: 元のコマンド

        Returns:
            RecoverySession: 復旧セッション結果
        """
        session_id = f"recovery_session_{int(time.time() * 1000)}"
        self.logger.info(f"包括的な復旧処理を開始: {session_id}")

        with self._recovery_lock:
            session = RecoverySession(
                session_id=session_id,
                recovery_context={
                    "failed_process_pid": failed_process.pid
                    if failed_process
                    else None,
                    "workflow_file": str(workflow_file) if workflow_file else None,
                    "original_command": original_command,
                },
            )
            self._current_session = session

        session_start_time = time.time()

        try:
            # ステップ1: 出力バッファクリア
            self.logger.info("復旧ステップ1: 出力バッファクリア")
            self.clear_output_buffers()

            # ステップ2: ハングしたプロセスの再起動
            if failed_process:
                self.logger.info("復旧ステップ2: ハングプロセス再起動")
                subprocess_restart_success = self.restart_hung_subprocess(
                    failed_process
                )
                if subprocess_restart_success:
                    session.recovery_context["subprocess_restart"] = "success"
                else:
                    session.recovery_context["subprocess_restart"] = "failed"

            # ステップ3: Docker再接続
            self.logger.info("復旧ステップ3: Docker再接続")
            docker_reconnect_success = self.attempt_docker_reconnection()
            if docker_reconnect_success:
                session.recovery_context["docker_reconnection"] = "success"
            else:
                session.recovery_context["docker_reconnection"] = "failed"

            # ステップ4: コンテナ状態リセット
            self.logger.info("復旧ステップ4: コンテナ状態リセット")
            container_reset_success = self.reset_container_state()
            if container_reset_success:
                session.recovery_context["container_reset"] = "success"
            else:
                session.recovery_context["container_reset"] = "failed"

            # ステップ5: フォールバック実行（必要に応じて）
            if workflow_file and original_command and self.enable_fallback_mode:
                # 主要復旧が失敗した場合のみフォールバックを実行
                primary_recovery_success = (
                    docker_reconnect_success
                    and container_reset_success
                    and (not failed_process or subprocess_restart_success)
                )

                if not primary_recovery_success:
                    self.logger.info("復旧ステップ5: フォールバック実行")
                    fallback_result = self.execute_fallback_mode(
                        workflow_file, original_command
                    )
                    session.fallback_mode_activated = True
                    session.recovery_context["fallback_execution"] = {
                        "success": fallback_result.success,
                        "method": fallback_result.fallback_method,
                    }

            # 全体的な成功判定
            successful_attempts = [
                attempt
                for attempt in session.attempts
                if attempt.status == RecoveryStatus.SUCCESS
            ]

            session.overall_success = (
                len(successful_attempts) >= len(session.attempts) * 0.6
            )  # 60%以上成功

            if session.overall_success:
                self.logger.success(
                    f"包括的復旧処理が成功しました: {len(successful_attempts)}/{len(session.attempts)} 成功"
                )
            else:
                self.logger.warning(
                    f"包括的復旧処理が部分的に成功しました: {len(successful_attempts)}/{len(session.attempts)} 成功"
                )

        except Exception as e:
            self.logger.error(f"包括的復旧処理中にエラーが発生しました: {str(e)}")
            session.overall_success = False
            session.recovery_context["error"] = str(e)

        finally:
            session.end_time = datetime.now(timezone.utc).isoformat()
            session.total_duration_ms = (time.time() - session_start_time) * 1000

            with self._recovery_lock:
                self._recovery_history.append(session)
                self._current_session = None

        return session

    def get_recovery_statistics(self) -> Dict[str, Any]:
        """
        復旧統計情報を取得

        Returns:
            Dict[str, Any]: 復旧統計情報
        """
        with self._recovery_lock:
            total_sessions = len(self._recovery_history)
            successful_sessions = sum(
                1 for session in self._recovery_history if session.overall_success
            )

            recovery_type_stats = {}
            for session in self._recovery_history:
                for attempt in session.attempts:
                    recovery_type = attempt.recovery_type.value
                    if recovery_type not in recovery_type_stats:
                        recovery_type_stats[recovery_type] = {"total": 0, "success": 0}

                    recovery_type_stats[recovery_type]["total"] += 1
                    if attempt.status == RecoveryStatus.SUCCESS:
                        recovery_type_stats[recovery_type]["success"] += 1

            return {
                "total_sessions": total_sessions,
                "successful_sessions": successful_sessions,
                "success_rate": successful_sessions / total_sessions
                if total_sessions > 0
                else 0.0,
                "recovery_type_statistics": recovery_type_stats,
                "current_session_active": self._current_session is not None,
                "last_session_time": self._recovery_history[-1].start_time
                if self._recovery_history
                else None,
            }

    # プライベートメソッド

    def _restart_docker_daemon(self) -> bool:
        """Docker daemonを再起動"""
        try:
            # systemctl を使用してDocker daemonを再起動
            result = subprocess.run(
                ["sudo", "systemctl", "restart", "docker"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            # systemctl が使用できない場合やsudo権限がない場合
            self.logger.debug("systemctl でのDocker daemon再起動に失敗")
            return False

    def _fix_docker_socket_permissions(self) -> bool:
        """Docker socket権限を修正"""
        try:
            socket_path = Path("/var/run/docker.sock")
            if socket_path.exists():
                # ソケットファイルの権限を確認・修正
                result = subprocess.run(
                    ["sudo", "chmod", "666", str(socket_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            self.logger.debug("Docker socket権限修正に失敗")
        return False

    def _stop_act_containers(self) -> int:
        """actコンテナを停止"""
        try:
            # act関連のコンテナを検索
            result = subprocess.run(
                ["docker", "ps", "-q", "--filter", "name=act"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout.strip():
                container_ids = result.stdout.strip().split("\n")

                # コンテナを停止
                stop_result = subprocess.run(
                    ["docker", "stop"] + container_ids,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                return len(container_ids) if stop_result.returncode == 0 else 0

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return 0

    def _remove_orphaned_containers(self) -> int:
        """孤立したコンテナを削除"""
        try:
            result = subprocess.run(
                ["docker", "container", "prune", "-f"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # 削除されたコンテナ数を推定（実際の数は取得困難）
            return 1 if result.returncode == 0 else 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return 0

    def _cleanup_unused_networks(self) -> int:
        """未使用ネットワークを削除"""
        try:
            result = subprocess.run(
                ["docker", "network", "prune", "-f"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return 1 if result.returncode == 0 else 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return 0

    def _cleanup_unused_volumes(self) -> int:
        """未使用ボリュームを削除"""
        try:
            result = subprocess.run(
                ["docker", "volume", "prune", "-f"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return 1 if result.returncode == 0 else 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return 0

    def _run_docker_system_prune(self) -> bool:
        """Docker system pruneを実行"""
        try:
            result = subprocess.run(
                ["docker", "system", "prune", "-f"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _fallback_direct_docker_run(
        self, workflow_file: Path
    ) -> FallbackExecutionResult:
        """直接Dockerコンテナでワークフローを実行するフォールバック"""
        start_time = time.time()

        try:
            # 基本的なDockerコンテナでワークフローをシミュレート
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{workflow_file.parent}:/workspace",
                    "alpine:latest",
                    "sh",
                    "-c",
                    f"echo 'ワークフローファイル解析: {workflow_file.name}' && cat /workspace/{workflow_file.name}",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            execution_time_ms = (time.time() - start_time) * 1000

            return FallbackExecutionResult(
                success=result.returncode == 0,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time_ms=execution_time_ms,
                fallback_method="direct_docker_run",
                limitations=[
                    "実際のGitHub Actionsの実行ではなく、ワークフローファイルの表示のみ",
                    "環境変数やシークレットは利用できません",
                ],
                warnings=[
                    "これは簡易的なフォールバック実行です",
                    "完全なワークフロー実行ではありません",
                ],
            )

        except Exception as e:
            return FallbackExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"直接Docker実行エラー: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
                fallback_method="direct_docker_run",
                limitations=[f"実行エラー: {str(e)}"],
            )

    def _fallback_simplified_act_execution(
        self, workflow_file: Path
    ) -> FallbackExecutionResult:
        """簡略化されたact実行フォールバック"""
        start_time = time.time()

        try:
            # 最小限のactコマンドで実行
            result = subprocess.run(
                ["act", "--dry-run", "--verbose", "-W", str(workflow_file.parent)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=workflow_file.parent,
            )

            execution_time_ms = (time.time() - start_time) * 1000

            return FallbackExecutionResult(
                success=result.returncode == 0,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time_ms=execution_time_ms,
                fallback_method="simplified_act_execution",
                limitations=[
                    "ドライランモードでの実行",
                    "実際のジョブは実行されません",
                ],
                warnings=[
                    "これは簡略化されたact実行です",
                    "完全な機能は利用できません",
                ],
            )

        except Exception as e:
            return FallbackExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"簡略化act実行エラー: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
                fallback_method="simplified_act_execution",
                limitations=[f"実行エラー: {str(e)}"],
            )

    def _fallback_dry_run_mode(self, workflow_file: Path) -> FallbackExecutionResult:
        """ドライランモードフォールバック"""
        start_time = time.time()

        try:
            # ワークフローファイルの基本的な解析と表示
            workflow_content = workflow_file.read_text()

            # 基本的なワークフロー情報を抽出
            lines = workflow_content.split("\n")
            job_count = sum(1 for line in lines if line.strip().startswith("- name:"))

            output = f"""
ドライランモード実行結果:
ワークフローファイル: {workflow_file.name}
ファイルサイズ: {len(workflow_content)} 文字
推定ジョブ数: {job_count}

ワークフロー内容:
{workflow_content[:500]}{"..." if len(workflow_content) > 500 else ""}
"""

            execution_time_ms = (time.time() - start_time) * 1000

            return FallbackExecutionResult(
                success=True,
                returncode=0,
                stdout=output,
                stderr="",
                execution_time_ms=execution_time_ms,
                fallback_method="dry_run_mode",
                limitations=[
                    "ワークフローファイルの表示のみ",
                    "実際の実行は行われません",
                ],
                warnings=[
                    "これはドライランモードです",
                    "実際のGitHub Actions実行ではありません",
                ],
            )

        except Exception as e:
            return FallbackExecutionResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"ドライランモードエラー: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
                fallback_method="dry_run_mode",
                limitations=[f"実行エラー: {str(e)}"],
            )

    def _record_recovery_attempt(self, attempt: RecoveryAttempt) -> None:
        """復旧試行を記録"""
        with self._recovery_lock:
            if self._current_session:
                self._current_session.attempts.append(attempt)
