"""
GitHub Actions Simulator - Enhanced Act Wrapper
既存のActWrapperを拡張し、診断機能とデッドロック検出メカニズムを統合した
安全なサブプロセス作成と出力ストリーミング機能を提供します。
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

# ActWrapperの機能は直接統合されました
from services.actions.execution_tracer import ExecutionTracer, ExecutionStage, ThreadState
from services.actions.logger import ActionsLogger


@dataclass
class DeadlockIndicator:
    """デッドロック指標"""

    indicator_type: str  # "thread_blocked", "process_hung", "output_stalled"
    severity: str  # "low", "medium", "high", "critical"
    description: str
    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    thread_id: Optional[int] = None
    process_id: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamResult:
    """出力ストリーミング結果"""

    stdout_lines: List[str] = field(default_factory=list)
    stderr_lines: List[str] = field(default_factory=list)
    stdout_bytes: int = 0
    stderr_bytes: int = 0
    threads_completed: bool = False
    deadlock_detected: bool = False
    deadlock_indicators: List[DeadlockIndicator] = field(default_factory=list)
    stream_duration_ms: float = 0.0
    error_message: Optional[str] = None


@dataclass
class MonitoredProcess:
    """監視対象プロセス"""

    process: subprocess.Popen
    command: List[str]
    start_time: float
    timeout_seconds: float
    heartbeat_interval: float = 30.0
    last_heartbeat: float = field(default_factory=time.time)
    output_stalled_threshold: float = 60.0  # 出力が停止したと判断する時間（秒）
    last_output_time: float = field(default_factory=time.time)
    deadlock_indicators: List[DeadlockIndicator] = field(default_factory=list)


@dataclass
class DetailedResult:
    """詳細な実行結果"""

    success: bool
    returncode: int
    stdout: str
    stderr: str
    command: str
    execution_time_ms: float = 0.0
    diagnostic_results: List[Dict[str, Any]] = field(default_factory=list)
    deadlock_indicators: List[DeadlockIndicator] = field(default_factory=list)
    stream_result: Optional[StreamResult] = None
    hang_analysis: Optional[Dict[str, Any]] = None
    resource_usage: List[Dict[str, Any]] = field(default_factory=list)
    trace_id: Optional[str] = None


class EnhancedActWrapper:
    """
    診断機能とデッドロック検出メカニズムを統合したActWrapperの拡張版

    主な機能:
    - 詳細な診断情報の収集
    - デッドロック検出と予防
    - 安全なサブプロセス管理
    - 出力ストリーミングの監視
    - ハングアップ分析
    """

    def __init__(
        self,
        working_directory: Optional[str] = None,
        *,
        config: Mapping[str, Any] | None = None,
        logger: ActionsLogger | None = None,
        execution_tracer: Optional[ExecutionTracer] = None,
        enable_diagnostics: bool = True,
        deadlock_detection_interval: float = 10.0,
        output_stall_threshold: float = 60.0,
    ) -> None:
        """
        EnhancedActWrapperを初期化

        Args:
            working_directory: 作業ディレクトリ
            config: 設定情報
            logger: ロガー
            execution_tracer: 実行トレーサー
            enable_diagnostics: 診断機能を有効にするかどうか
            deadlock_detection_interval: デッドロック検出の間隔（秒）
            output_stall_threshold: 出力停止と判断する時間（秒）
        """
        # ActWrapperの初期化ロジックを統合
        self.working_directory = Path(working_directory or os.getcwd()).resolve()
        if not self.working_directory.exists():
            raise RuntimeError(
                f"作業ディレクトリが存在しません: {self.working_directory}"
            )
        self.logger = logger or ActionsLogger(verbose=False)
        self.execution_tracer = execution_tracer or ExecutionTracer(logger=self.logger)

        # ActRunnerSettingsの初期化（簡略化）
        self.settings = self._create_default_settings(config)

        engine_name = os.getenv("ACTIONS_SIMULATOR_ENGINE", "act").strip()
        self._engine = engine_name.lower() or "act"
        self._mock_mode = self._engine in {"mock", "stub", "fake", "noop"}
        mock_delay = os.getenv("ACTIONS_SIMULATOR_MOCK_DELAY_SECONDS")
        try:
            self._mock_delay_seconds = (
                max(0.0, float(mock_delay)) if mock_delay else 0.0
            )
        except ValueError:
            self._mock_delay_seconds = 0.0

        self._timeout_seconds = self._resolve_timeout_seconds(config)
        if self._timeout_seconds != 600:
            self.logger.info(
                f"act 実行タイムアウトを {self._timeout_seconds} 秒に設定しました",
            )

        if self._mock_mode:
            self.act_binary = "mock-act"
            self.logger.debug(
                f"ACTIONS_SIMULATOR_ENGINE={engine_name} のためモックモードで実行します",
            )
        else:
            self.act_binary = self._find_act_binary()

        self.enable_diagnostics = enable_diagnostics
        self.deadlock_detection_interval = deadlock_detection_interval
        self.output_stall_threshold = output_stall_threshold

        # 診断サービスの初期化（遅延インポートでサイクル依存を回避）
        self._diagnostic_service = None
        if self.enable_diagnostics:
            self._initialize_diagnostic_service()

        # デッドロック検出用の状態管理
        self._active_processes: Dict[int, MonitoredProcess] = {}
        self._monitoring_threads: List[threading.Thread] = []
        self._stop_monitoring = threading.Event()

        # 自動復旧機能の初期化
        self._auto_recovery = None
        self._initialize_auto_recovery()

    def run_workflow(
        self,
        workflow_file: Optional[str] = None,
        event: str | None = None,
        job: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute a workflow through act and return structured output."""

        # 診断機能が有効な場合は詳細実行を使用
        if self.enable_diagnostics:
            detailed_result = self.run_workflow_with_diagnostics(
                workflow_file=workflow_file,
                event=event,
                job=job,
                dry_run=dry_run,
                verbose=verbose,
                env_vars=env_vars,
            )
            return {
                "success": detailed_result.success,
                "returncode": detailed_result.returncode,
                "stdout": detailed_result.stdout,
                "stderr": detailed_result.stderr,
                "command": detailed_result.command,
            }
        else:
            # 基本実行
            return self._run_workflow_with_enhanced_monitoring(
                workflow_file=workflow_file,
                event=event,
                job=job,
                dry_run=dry_run,
                verbose=verbose,
                env_vars=env_vars,
            )

    def _create_default_settings(self, config: Mapping[str, Any] | None):
        """デフォルト設定を作成"""
        from dataclasses import dataclass, field
        from typing import Dict

        @dataclass(frozen=True)
        class ActRunnerSettings:
            image: str | None = None
            platforms: tuple[str, ...] = field(default_factory=tuple)
            container_workdir: str | None = None
            cache_dir: str | None = "/opt/act/cache"
            env: Dict[str, str] = field(default_factory=dict)

        return ActRunnerSettings()

    def _find_act_binary(self) -> str:
        """Locate the act binary in the current environment."""
        import shutil

        candidates = [
            shutil.which("act"),
            "/home/linuxbrew/.linuxbrew/bin/act",
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                self.logger.debug(f"actバイナリが見つかりました: {candidate}")
                return candidate

        raise RuntimeError(
            "actが見つかりません。以下のいずれかでインストールしてください:\n"
            "  - curl -fsSL https://raw.githubusercontent.com/"
            "nektos/act/master/install.sh | sudo bash\n"
            "  - brew install act"
        )

    def _resolve_timeout_seconds(self, config: Mapping[str, Any] | None) -> int:
        """Resolve timeout configuration."""
        default_timeout = 600
        timeout_value = default_timeout

        if isinstance(config, Mapping):
            timeouts_section = config.get("timeouts")
            if isinstance(timeouts_section, Mapping):
                candidate = timeouts_section.get("act_seconds")
                if isinstance(candidate, (int, float)) and candidate > 0:
                    timeout_value = int(candidate)

        env_candidate = os.getenv("ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS")
        if env_candidate:
            try:
                env_timeout = int(float(env_candidate.strip()))
                if env_timeout > 0:
                    timeout_value = env_timeout
            except (ValueError, TypeError):
                pass

        return timeout_value



    def _ensure_git_repository(self) -> None:
        """Ensure the working directory is a proper Git repository."""
        git_dir = self.working_directory / ".git"

        if git_dir.exists():
            self.logger.debug("Gitリポジトリが既に存在します")
            return

        try:
            # Initialize Git repository
            subprocess.run(
                ["git", "init"],
                cwd=self.working_directory,
                capture_output=True,
                text=True,
                check=True,
            )
            self.logger.debug("Gitリポジトリを初期化しました")

            # Set basic Git configuration if not set
            try:
                subprocess.run(
                    ["git", "config", "user.name", "Actions Simulator"],
                    cwd=self.working_directory,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                subprocess.run(
                    ["git", "config", "user.email", "simulator@localhost"],
                    cwd=self.working_directory,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.logger.debug("Git設定を初期化しました")
            except subprocess.CalledProcessError:
                # Git config might already be set globally
                pass

            # Add a remote origin if it doesn't exist
            try:
                subprocess.run(
                    ["git", "remote", "add", "origin", "https://github.com/local/example.git"],
                    cwd=self.working_directory,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.logger.debug("Gitリモートを設定しました")
            except subprocess.CalledProcessError:
                # Remote might already exist
                pass

        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Gitリポジトリの初期化に失敗しました: {e}")

    def _ensure_docker_permissions(self) -> None:
        """Ensure Docker daemon is accessible."""
        try:
            # Test Docker connectivity
            result = subprocess.run(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                self.logger.debug(f"Docker接続確認: サーバーバージョン {result.stdout.strip()}")
                return
            else:
                self.logger.warning(f"Docker接続テスト失敗: {result.stderr}")

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.logger.warning(f"Docker接続確認エラー: {e}")

        # Try to fix common Docker permission issues
        docker_sock = Path("/var/run/docker.sock")
        if docker_sock.exists():
            try:
                # Check current permissions
                stat_info = docker_sock.stat()
                self.logger.debug(f"Docker socket権限: {oct(stat_info.st_mode)}, GID: {stat_info.st_gid}")

                # Try to add current user to docker group (if running as root or with sudo)
                current_user = os.getenv("USER", "actions")
                if current_user != "root":
                    try:
                        subprocess.run(
                            ["usermod", "-aG", "docker", current_user],
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                        self.logger.debug(f"ユーザー {current_user} をdockerグループに追加しました")
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        # usermod might not be available or we don't have permissions
                        pass

            except (OSError, PermissionError) as e:
                self.logger.debug(f"Docker権限確認エラー: {e}")

    def _cleanup_act_workaround(self) -> None:
        """Clean up temporary workflow files created for act."""
        # No longer creating temporary files, so no cleanup needed
        pass

    def _compose_runner_flags(self) -> list[str]:
        """Compose runner flags for act execution."""
        flags: list[str] = []

        # 非対話的実行を強制するフラグを追加
        flags.extend(["--rm"])

        if self.settings.container_workdir:
            flags.extend(["--container-workdir", self.settings.container_workdir])
        if self.settings.image:
            platforms = self.settings.platforms or ("ubuntu-latest",)
            for platform in platforms:
                flags.extend(["-P", f"{platform}={self.settings.image}"])
        elif self.settings.platforms:
            for platform in self.settings.platforms:
                flags.extend(["--platform", platform])
        else:
            # デフォルトプラットフォームを明示的に設定
            flags.extend(["-P", "ubuntu-latest=catthehacker/ubuntu:act-latest"])

        return flags

    def _compose_env_args(
        self,
        overrides: Mapping[str, str] | None,
    ) -> list[str]:
        """Compose environment arguments for act execution."""
        combined: Dict[str, str] = dict(self.settings.env)
        if overrides:
            combined.update({str(k): str(v) for k, v in overrides.items()})

        args: list[str] = []
        for key, value in combined.items():
            args.extend(["--env", f"{key}={value}"])
        return args

    def _build_process_env(
        self,
        default_event: str | None,
        overrides: Mapping[str, str] | None,
    ) -> Dict[str, str]:
        """Build process environment variables."""
        env = os.environ.copy()

        # 非対話的実行を強制する環境変数を設定
        env["ACT_LOG_LEVEL"] = "info"
        env["ACT_PLATFORM"] = "ubuntu-latest=catthehacker/ubuntu:act-latest"
        env["DOCKER_HOST"] = "unix:///var/run/docker.sock"

        # Git関連の環境変数を設定（act実行時のGitエラー回避）
        env["GIT_AUTHOR_NAME"] = "Actions Simulator"
        env["GIT_AUTHOR_EMAIL"] = "simulator@localhost"
        env["GIT_COMMITTER_NAME"] = "Actions Simulator"
        env["GIT_COMMITTER_EMAIL"] = "simulator@localhost"

        # GitHub Actions互換の環境変数を設定
        env["GITHUB_WORKSPACE"] = str(self.working_directory)
        env["GITHUB_WORKFLOW"] = "CI"
        env["GITHUB_RUN_ID"] = "1"
        env["GITHUB_RUN_NUMBER"] = "1"
        env["GITHUB_SHA"] = "0000000000000000000000000000000000000000"
        env["GITHUB_REF_NAME"] = "main"
        env["GITHUB_REF_TYPE"] = "branch"
        env["GITHUB_REPOSITORY_OWNER"] = "local"
        env["GITHUB_ACTOR_ID"] = "1"
        env["GITHUB_TRIGGERING_ACTOR"] = "local-runner"

        # ワークフローディレクトリを明示的に指定（パス解決問題の回避）
        workflows_dir = self.working_directory / ".github" / "workflows"
        if workflows_dir.exists():
            env["GITHUB_WORKFLOW_DIR"] = str(workflows_dir)
            env["ACT_WORKFLOW_DIR"] = str(workflows_dir)
            # actの作業ディレクトリを設定
            env["ACT_WORKDIR"] = str(self.working_directory)

        # Docker関連の環境変数
        env["DOCKER_BUILDKIT"] = "1"
        env["COMPOSE_DOCKER_CLI_BUILD"] = "1"

        if self.settings.cache_dir:
            env.setdefault("ACT_CACHE_DIR", self.settings.cache_dir)
        if default_event and "GITHUB_EVENT_NAME" not in env:
            env["GITHUB_EVENT_NAME"] = default_event
        if overrides:
            env.update({str(k): str(v) for k, v in overrides.items()})
        return env

    def _initialize_diagnostic_service(self) -> None:
        """診断サービスを初期化"""
        try:
            # 遅延インポートでサイクル依存を回避
            import sys
            sys.path.append(str(Path(__file__).parent.parent.parent / "src"))
            from diagnostic_service import DiagnosticService

            self._diagnostic_service = DiagnosticService(logger=self.logger)
            self.logger.debug("診断サービスを初期化しました")
        except (ImportError, ModuleNotFoundError) as e:
            self.logger.warning(f"診断サービスの初期化に失敗しました: {e}")
            self.enable_diagnostics = False
            self._diagnostic_service = None

    def _initialize_auto_recovery(self) -> None:
        """自動復旧機能を初期化"""
        try:
            from services.actions.auto_recovery import AutoRecovery
            from services.actions.docker_integration_checker import DockerIntegrationChecker

            docker_checker = DockerIntegrationChecker(logger=self.logger)
            self._auto_recovery = AutoRecovery(
                logger=self.logger,
                docker_checker=docker_checker,
                max_recovery_attempts=3,
                recovery_timeout=60.0,
                enable_fallback_mode=True,
            )
            self.logger.debug("自動復旧機能を初期化しました")
        except (ImportError, ModuleNotFoundError) as e:
            self.logger.warning(f"自動復旧機能の初期化に失敗しました: {e}")
            self._auto_recovery = None

    @property
    def auto_recovery(self):
        """自動復旧インスタンスを取得"""
        return self._auto_recovery

    @property
    def diagnostic_service(self):
        """診断サービスを取得"""
        return self._diagnostic_service

    @property
    def process_monitor(self):
        """プロセス監視を取得（ExecutionTracerを返す）"""
        return self.execution_tracer

    @property
    def docker_integration_checker(self):
        """Docker統合チェッカーを取得"""
        if self._auto_recovery:
            return self._auto_recovery.docker_checker
        return None

    @property
    def hangup_detector(self):
        """ハングアップ検出器を取得（ExecutionTracerを返す）"""
        return self.execution_tracer

    def run_workflow_with_diagnostics(
        self,
        workflow_file: Optional[str] = None,
        event: str | None = None,
        job: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> DetailedResult:
        """
        診断機能付きでワークフローを実行

        Args:
            workflow_file: ワークフローファイル
            event: イベント名
            job: ジョブ名
            dry_run: ドライラン実行
            verbose: 詳細ログ
            env_vars: 環境変数

        Returns:
            DetailedResult: 詳細な実行結果
        """
        start_time = time.time()
        trace_id = f"enhanced_act_{int(start_time * 1000)}"

        # 実行前診断チェック
        diagnostic_results = []
        if self.enable_diagnostics and self._diagnostic_service:
            self.logger.info("実行前診断チェックを開始します...")
            pre_check = self._diagnostic_service.run_comprehensive_health_check()
            diagnostic_results.append({
                "phase": "pre_execution",
                "timestamp": time.time(),
                "results": pre_check
            })

            # 重大な問題がある場合は実行を中止
            if pre_check.get("overall_status") == "ERROR":
                error_msg = f"実行前診断で重大な問題が検出されました: {pre_check.get('summary')}"
                self.logger.error(error_msg)
                return DetailedResult(
                    success=False,
                    returncode=-1,
                    stdout="",
                    stderr=error_msg,
                    command="enhanced-act (診断失敗)",
                    execution_time_ms=(time.time() - start_time) * 1000,
                    diagnostic_results=diagnostic_results,
                    trace_id=trace_id
                )

        try:
            # 通常のワークフロー実行（拡張監視付き）
            result = self._run_workflow_with_enhanced_monitoring(
                workflow_file=workflow_file,
                event=event,
                job=job,
                dry_run=dry_run,
                verbose=verbose,
                env_vars=env_vars,
                trace_id=trace_id
            )

            # 実行後診断チェック
            if self.enable_diagnostics and self._diagnostic_service:
                self.logger.info("実行後診断チェックを開始します...")
                post_check = self._diagnostic_service.run_comprehensive_health_check()
                diagnostic_results.append({
                    "phase": "post_execution",
                    "timestamp": time.time(),
                    "results": post_check
                })

            # 詳細結果を構築
            execution_time_ms = (time.time() - start_time) * 1000
            detailed_result = DetailedResult(
                success=result.get("success", False),
                returncode=result.get("returncode", -1),
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                command=result.get("command", ""),
                execution_time_ms=execution_time_ms,
                diagnostic_results=diagnostic_results,
                trace_id=trace_id
            )

            # ハングアップ分析を追加
            if not result.get("success", False):
                detailed_result.hang_analysis = self._analyze_execution_failure(result)

            return detailed_result

        except Exception as e:
            self.logger.error(f"拡張ワークフロー実行中にエラーが発生しました: {e}")
            return DetailedResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(e),
                command="enhanced-act (実行エラー)",
                execution_time_ms=(time.time() - start_time) * 1000,
                diagnostic_results=diagnostic_results,
                trace_id=trace_id
            )

    def _run_workflow_with_enhanced_monitoring(
        self,
        workflow_file: Optional[str] = None,
        event: str | None = None,
        job: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
        env_vars: Optional[Dict[str, str]] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        拡張監視機能付きでワークフローを実行

        Args:
            workflow_file: ワークフローファイル
            event: イベント名
            job: ジョブ名
            dry_run: ドライラン実行
            verbose: 詳細ログ
            env_vars: 環境変数
            trace_id: トレースID

        Returns:
            Dict[str, Any]: 実行結果
        """
        # モックモードの場合は親クラスの実装を使用
        if self._mock_mode:
            return super().run_workflow(
                workflow_file=workflow_file,
                event=event,
                job=job,
                dry_run=dry_run,
                verbose=verbose,
                env_vars=env_vars,
            )

        # 実行トレースを開始
        if trace_id and self.execution_tracer:
            self.execution_tracer.start_trace()

        try:
            # コマンドを構築
            cmd = self._build_enhanced_command(
                workflow_file=workflow_file,
                job=job,
                dry_run=dry_run,
                verbose=verbose,
                env_vars=env_vars
            )

            process_env = self._build_process_env(event, env_vars)

            self.logger.info(f"拡張監視付きactコマンド実行: {' '.join(cmd)}")

            # 監視付きサブプロセスを作成
            monitored_process = self._create_monitored_subprocess(
                cmd, process_env, self._timeout_seconds
            )

            # 安全な出力ストリーミングを実行
            stream_result = self._handle_output_streaming_safely(monitored_process)

            # プロセス完了を待機
            return_code = self._wait_for_process_completion(monitored_process)

            # 結果を構築
            stdout_text = "".join(stream_result.stdout_lines)
            stderr_text = "".join(stream_result.stderr_lines)

            success = return_code == 0 and not stream_result.deadlock_detected
            if stream_result.deadlock_detected:
                stderr_text += f"\nデッドロックが検出されました: {len(stream_result.deadlock_indicators)}個の指標"

            return {
                "success": success,
                "returncode": return_code,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "command": " ".join(cmd),
                "stream_result": stream_result,
                "deadlock_indicators": stream_result.deadlock_indicators,
            }

        finally:
            # 監視を停止
            self._stop_all_monitoring()

            # トレースを終了
            if trace_id and self.execution_tracer:
                self.execution_tracer.stop_trace()

    def _build_enhanced_command(
        self,
        workflow_file: Optional[str] = None,
        job: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        """
        拡張監視用のコマンドを構築

        Args:
            workflow_file: ワークフローファイル
            job: ジョブ名
            dry_run: ドライラン実行
            verbose: 詳細ログ
            env_vars: 環境変数

        Returns:
            List[str]: 構築されたコマンド
        """
        cmd: List[str] = [self.act_binary]
        cmd.extend(self._compose_runner_flags())

        if workflow_file:
            # 環境設定を確実に実行
            self._ensure_git_repository()
            self._ensure_docker_permissions()

            # シンプルなパス解決: actのパス重複バグを回避するため絶対パスを使用
            workflow_name = Path(workflow_file).name

            # working_directoryが既に.github/workflowsの場合は直接使用
            if str(self.working_directory).endswith("/.github/workflows"):
                absolute_workflow_path = self.working_directory / workflow_name
            else:
                absolute_workflow_path = self.working_directory / ".github" / "workflows" / workflow_name

            if absolute_workflow_path.exists():
                final_workflow = str(absolute_workflow_path)
                self.logger.info(f"絶対パスを使用: {workflow_file} -> {final_workflow}")
            else:
                # フォールバック: 元のパスを使用
                final_workflow = workflow_file
                self.logger.warning(f"ワークフローファイルが見つかりません: {absolute_workflow_path}")

            cmd.extend(["-W", final_workflow])
        if job:
            cmd.extend(["-j", job])
        if dry_run:
            cmd.append("--dryrun")
        if verbose:
            cmd.append("--verbose")

        # 拡張監視用のフラグを追加
        cmd.extend(["--rm"])  # コンテナの自動削除

        # デフォルトのGitHub Actions環境変数を追加
        default_env_vars = {
            "GITHUB_USER": "local-runner",
            "GITHUB_ACTOR": "local-runner",
            "GITHUB_REPOSITORY": "local/example",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_REF": "refs/heads/main",
        }

        # ユーザー指定の環境変数とマージ
        merged_env_vars = {**default_env_vars, **(env_vars or {})}

        env_args = self._compose_env_args(merged_env_vars)
        cmd.extend(env_args)

        return cmd

    def _create_monitored_subprocess(
        self, cmd: List[str], env: Dict[str, str], timeout_seconds: float
    ) -> MonitoredProcess:
        """
        監視付きサブプロセスを作成

        Args:
            cmd: 実行コマンド
            env: 環境変数
            timeout_seconds: タイムアウト時間

        Returns:
            MonitoredProcess: 監視対象プロセス
        """
        self.execution_tracer.set_stage(ExecutionStage.SUBPROCESS_CREATION)

        try:
            # サブプロセスを作成
            process = subprocess.Popen(
                cmd,
                cwd=self.working_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None,  # プロセスグループを作成
            )

            self.logger.info(f"監視付きプロセス開始: PID={process.pid}")

            # 監視対象プロセスを作成
            monitored_process = MonitoredProcess(
                process=process,
                command=cmd,
                start_time=time.time(),
                timeout_seconds=timeout_seconds,
                heartbeat_interval=30.0,
                output_stalled_threshold=self.output_stall_threshold,
            )

            # プロセス監視に追加
            self._active_processes[process.pid] = monitored_process

            # 実行トレースに追加
            self.execution_tracer.trace_subprocess_execution(
                cmd, process, str(self.working_directory)
            )

            # デッドロック監視スレッドを開始
            self._start_deadlock_monitoring(monitored_process)

            return monitored_process

        except (OSError, subprocess.SubprocessError) as exc:
            self.logger.error(f"監視付きプロセス作成エラー: {exc}")
            self.execution_tracer.set_stage(ExecutionStage.FAILED)
            raise

    def _handle_output_streaming_safely(self, monitored_process: MonitoredProcess) -> StreamResult:
        """
        安全な出力ストリーミングを実行

        Args:
            monitored_process: 監視対象プロセス

        Returns:
            StreamResult: ストリーミング結果
        """
        self.execution_tracer.set_stage(ExecutionStage.OUTPUT_STREAMING)

        start_time = time.time()
        stream_result = StreamResult()

        def _safe_stream_output(
            pipe: Any,
            collector: List[str],
            label: str,
            thread_trace,
        ) -> None:
            """安全な出力ストリーミング関数"""
            try:
                self.execution_tracer.update_thread_state(
                    thread_trace, ThreadState.RUNNING
                )

                if pipe is None:
                    return

                with pipe:
                    for raw_line in pipe:
                        collector.append(raw_line)
                        line = raw_line.rstrip("\n")
                        if line:
                            # 出力時刻を更新
                            monitored_process.last_output_time = time.time()

                            # 出力を表示
                            print(f"[{label}] {line}")
                            if self.logger.verbose:
                                self.logger.debug(f"[{label}] {line}")

                self.execution_tracer.update_thread_state(
                    thread_trace, ThreadState.TERMINATED
                )

            except Exception as e:
                self.execution_tracer.update_thread_state(
                    thread_trace, ThreadState.ERROR, str(e)
                )
                stream_result.error_message = str(e)

        # 出力ストリーミングスレッドを作成
        threads: List[threading.Thread] = []
        thread_traces = []

        process = monitored_process.process

        if process.stdout:
            t_out = threading.Thread(
                target=_safe_stream_output,
                args=(process.stdout, stream_result.stdout_lines, "act stdout", None),
                daemon=True,
                name="EnhancedActWrapper-StdoutStream",
            )
            thread_trace_out = self.execution_tracer.track_thread_lifecycle(
                t_out, "_safe_stream_output"
            )
            # スレッド関数の引数を更新
            t_out = threading.Thread(
                target=_safe_stream_output,
                args=(process.stdout, stream_result.stdout_lines, "act stdout", thread_trace_out),
                daemon=True,
                name="EnhancedActWrapper-StdoutStream",
            )
            t_out.start()
            threads.append(t_out)
            thread_traces.append(thread_trace_out)

        if process.stderr:
            t_err = threading.Thread(
                target=_safe_stream_output,
                args=(process.stderr, stream_result.stderr_lines, "act stderr", None),
                daemon=True,
                name="EnhancedActWrapper-StderrStream",
            )
            thread_trace_err = self.execution_tracer.track_thread_lifecycle(
                t_err, "_safe_stream_output"
            )
            # スレッド関数の引数を更新
            t_err = threading.Thread(
                target=_safe_stream_output,
                args=(process.stderr, stream_result.stderr_lines, "act stderr", thread_trace_err),
                daemon=True,
                name="EnhancedActWrapper-StderrStream",
            )
            t_err.start()
            threads.append(t_err)
            thread_traces.append(thread_trace_err)

        # スレッド完了を待機（タイムアウト付き）
        thread_timeout = 5.0
        for thread in threads:
            thread.join(timeout=thread_timeout)
            if thread.is_alive():
                self.logger.warning(f"出力ストリーミングスレッドがタイムアウトしました: {thread.name}")
                stream_result.deadlock_detected = True
                stream_result.deadlock_indicators.append(
                    DeadlockIndicator(
                        indicator_type="thread_blocked",
                        severity="high",
                        description=f"出力ストリーミングスレッド '{thread.name}' がタイムアウトしました",
                        thread_id=thread.ident,
                    )
                )

        # 結果を更新
        stream_result.threads_completed = all(not t.is_alive() for t in threads)
        stream_result.stdout_bytes = sum(len(line.encode('utf-8')) for line in stream_result.stdout_lines)
        stream_result.stderr_bytes = sum(len(line.encode('utf-8')) for line in stream_result.stderr_lines)
        stream_result.stream_duration_ms = (time.time() - start_time) * 1000

        # デッドロック指標を統合
        stream_result.deadlock_indicators.extend(monitored_process.deadlock_indicators)

        return stream_result

    def _wait_for_process_completion(self, monitored_process: MonitoredProcess) -> int:
        """
        プロセス完了を待機

        Args:
            monitored_process: 監視対象プロセス

        Returns:
            int: 終了コード
        """
        self.execution_tracer.set_stage(ExecutionStage.PROCESS_MONITORING)

        process = monitored_process.process
        start_time = monitored_process.start_time
        timeout_seconds = monitored_process.timeout_seconds

        while True:
            return_code = process.poll()
            if return_code is not None:
                break

            now = time.time()
            elapsed = now - start_time

            # タイムアウトチェック
            if elapsed >= timeout_seconds:
                self.logger.error(f"プロセス実行がタイムアウトしました (PID: {process.pid})")

                # プロセスを強制終了
                self._force_terminate_process(process)

                # ハングアップ検出
                hang_info = self.execution_tracer.detect_hang_condition(timeout_seconds)
                if hang_info:
                    self.logger.error(f"ハングアップを検出: {hang_info}")

                self.execution_tracer.set_stage(ExecutionStage.TIMEOUT)
                return -1

            # ハートビートログ
            if now >= monitored_process.last_heartbeat + monitored_process.heartbeat_interval:
                process_info = {
                    "pid": process.pid,
                    "elapsed_seconds": int(elapsed),
                    "return_code": process.poll(),
                }
                self.execution_tracer.log_heartbeat(
                    f"拡張監視 - act 実行中... {int(elapsed)} 秒経過 (PID: {process.pid})",
                    process_info,
                )
                monitored_process.last_heartbeat = now

            time.sleep(1)

        # プロセス完了
        if process.poll() is None:
            process.wait()

        return_code = process.returncode or 0

        if return_code != 0:
            self.logger.error(f"act 実行が失敗しました (returncode={return_code})")
            self.execution_tracer.set_stage(ExecutionStage.FAILED)
        else:
            self.execution_tracer.set_stage(ExecutionStage.COMPLETED)

        return return_code

    def _start_deadlock_monitoring(self, monitored_process: MonitoredProcess) -> None:
        """
        デッドロック監視を開始

        Args:
            monitored_process: 監視対象プロセス
        """
        def _deadlock_monitoring_loop():
            """デッドロック監視ループ"""
            while not self._stop_monitoring.is_set():
                try:
                    # デッドロック条件をチェック
                    indicators = self.detect_deadlock_conditions(monitored_process)
                    if indicators:
                        monitored_process.deadlock_indicators.extend(indicators)
                        for indicator in indicators:
                            self.logger.warning(
                                f"デッドロック指標を検出: {indicator.indicator_type} - {indicator.description}"
                            )

                    # 指定間隔で待機
                    self._stop_monitoring.wait(self.deadlock_detection_interval)

                except Exception as e:
                    self.logger.error(f"デッドロック監視中にエラーが発生しました: {e}")
                    time.sleep(1.0)

        # 監視スレッドを開始
        monitor_thread = threading.Thread(
            target=_deadlock_monitoring_loop,
            name=f"DeadlockMonitor-{monitored_process.process.pid}",
            daemon=True,
        )
        monitor_thread.start()
        self._monitoring_threads.append(monitor_thread)

        self.logger.debug(f"デッドロック監視を開始しました: PID {monitored_process.process.pid}")

    def detect_deadlock_conditions(self, monitored_process: MonitoredProcess) -> List[DeadlockIndicator]:
        """
        デッドロック条件を検出

        Args:
            monitored_process: 監視対象プロセス

        Returns:
            List[DeadlockIndicator]: 検出されたデッドロック指標
        """
        indicators = []
        now = time.time()
        process = monitored_process.process

        try:
            # プロセスが応答しているかチェック
            if process.poll() is None:  # プロセスが実行中
                # 出力が長時間停止しているかチェック
                output_stall_time = now - monitored_process.last_output_time
                if output_stall_time > monitored_process.output_stalled_threshold:
                    indicators.append(
                        DeadlockIndicator(
                            indicator_type="output_stalled",
                            severity="medium",
                            description=f"出力が {output_stall_time:.1f} 秒間停止しています",
                            process_id=process.pid,
                            details={"stall_duration": output_stall_time},
                        )
                    )

                # プロセスの実行時間が異常に長いかチェック
                execution_time = now - monitored_process.start_time
                if execution_time > monitored_process.timeout_seconds * 0.8:  # タイムアウトの80%
                    indicators.append(
                        DeadlockIndicator(
                            indicator_type="process_hung",
                            severity="high",
                            description=f"プロセスが {execution_time:.1f} 秒間実行中（タイムアウト間近）",
                            process_id=process.pid,
                            details={"execution_time": execution_time, "timeout": monitored_process.timeout_seconds},
                        )
                    )

        except Exception as e:
            indicators.append(
                DeadlockIndicator(
                    indicator_type="monitoring_error",
                    severity="low",
                    description=f"デッドロック監視中にエラーが発生しました: {str(e)}",
                    process_id=process.pid,
                    details={"error": str(e)},
                )
            )

        return indicators

    def _force_terminate_process(self, process: subprocess.Popen) -> None:
        """
        プロセスを強制終了

        Args:
            process: 終了するプロセス
        """
        try:
            if process.poll() is None:  # プロセスが実行中
                self.logger.warning(f"プロセスを強制終了します: PID {process.pid}")

                # まずSIGTERMを送信
                if hasattr(os, 'killpg') and hasattr(process, 'pid'):
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        time.sleep(2.0)  # 終了を待機
                    except (OSError, ProcessLookupError):
                        pass

                # まだ実行中の場合はSIGKILLを送信
                if process.poll() is None:
                    process.kill()
                    time.sleep(1.0)

                # 最終確認
                if process.poll() is None:
                    self.logger.error(f"プロセスの強制終了に失敗しました: PID {process.pid}")
                else:
                    self.logger.info(f"プロセスを正常に終了しました: PID {process.pid}")

        except Exception as e:
            self.logger.error(f"プロセス強制終了中にエラーが発生しました: {e}")

    def _stop_all_monitoring(self) -> None:
        """すべての監視を停止"""
        self._stop_monitoring.set()

        # 監視スレッドの終了を待機
        for thread in self._monitoring_threads:
            if thread.is_alive():
                thread.join(timeout=2.0)

        # アクティブプロセスをクリア
        self._active_processes.clear()
        self._monitoring_threads.clear()
        self._stop_monitoring.clear()

        self.logger.debug("すべての監視を停止しました")

    def _analyze_execution_failure(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        実行失敗の分析

        Args:
            result: 実行結果

        Returns:
            Dict[str, Any]: 失敗分析結果
        """
        analysis = {
            "failure_type": "unknown",
            "probable_causes": [],
            "recommendations": [],
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        returncode = result.get("returncode", 0)
        stderr = result.get("stderr", "")
        stream_result = result.get("stream_result")

        # 終了コードによる分析
        if returncode == -1:
            analysis["failure_type"] = "timeout"
            analysis["probable_causes"].append("実行タイムアウト")
            analysis["recommendations"].extend([
                "タイムアウト時間を延長してください",
                "ワークフローの複雑さを確認してください",
                "システムリソースを確認してください"
            ])
        elif returncode != 0:
            analysis["failure_type"] = "execution_error"
            analysis["probable_causes"].append(f"act実行エラー (終了コード: {returncode})")

        # デッドロック分析
        if stream_result and stream_result.deadlock_detected:
            analysis["failure_type"] = "deadlock"
            analysis["probable_causes"].append("デッドロック検出")
            analysis["recommendations"].extend([
                "出力ストリーミングの問題を確認してください",
                "プロセス間通信の問題を調査してください"
            ])

        # エラーメッセージ分析
        if "docker" in stderr.lower():
            analysis["probable_causes"].append("Docker関連の問題")
            analysis["recommendations"].extend([
                "Docker daemonが実行されているか確認してください",
                "Docker権限を確認してください"
            ])

        if "permission" in stderr.lower():
            analysis["probable_causes"].append("権限の問題")
            analysis["recommendations"].append("ファイル・ディレクトリの権限を確認してください")

        return analysis

    def force_cleanup_on_timeout(self) -> None:
        """タイムアウト時の強制クリーンアップ"""
        self.logger.warning("タイムアウトによる強制クリーンアップを開始します")

        # すべてのアクティブプロセスを強制終了
        for pid, monitored_process in list(self._active_processes.items()):
            self._force_terminate_process(monitored_process.process)

        # 監視を停止
        self._stop_all_monitoring()

        self.logger.info("強制クリーンアップが完了しました")

    def run_workflow_with_auto_recovery(
        self,
        workflow_file: Optional[str] = None,
        event: str | None = None,
        job: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
        env_vars: Optional[Dict[str, str]] = None,
        enable_recovery: bool = True,
        max_recovery_attempts: Optional[int] = None,
    ) -> DetailedResult:
        """
        自動復旧機能付きでワークフローを実行

        Args:
            workflow_file: ワークフローファイル
            event: イベント名
            job: ジョブ名
            dry_run: ドライラン実行
            verbose: 詳細ログ
            env_vars: 環境変数
            enable_recovery: 自動復旧を有効にするかどうか
            max_recovery_attempts: 最大復旧試行回数

        Returns:
            DetailedResult: 詳細な実行結果
        """
        start_time = time.time()
        trace_id = f"auto_recovery_act_{int(start_time * 1000)}"

        # 最初の実行を試行
        self.logger.info("プライマリワークフロー実行を開始します...")
        result = self.run_workflow_with_diagnostics(
            workflow_file=workflow_file,
            event=event,
            job=job,
            dry_run=dry_run,
            verbose=verbose,
            env_vars=env_vars,
        )

        # 成功した場合はそのまま返す
        if result.success:
            self.logger.info("プライマリ実行が成功しました")
            return result

        # 失敗した場合、自動復旧を試行
        if not enable_recovery or not self._auto_recovery:
            self.logger.info("自動復旧が無効または利用できません")
            return result

        self.logger.warning("プライマリ実行が失敗しました。自動復旧を試行します...")

        try:
            # 復旧セッションを開始
            recovery_session = self._auto_recovery.run_comprehensive_recovery(
                error_context={
                    "command": result.command,
                    "returncode": result.returncode,
                    "stderr": result.stderr,
                    "diagnostic_results": result.diagnostic_results,
                },
                max_attempts=max_recovery_attempts or 3,
            )

            if recovery_session.overall_success:
                self.logger.info("自動復旧が成功しました。ワークフローを再実行します...")

                # 復旧後に再実行
                retry_result = self.run_workflow_with_diagnostics(
                    workflow_file=workflow_file,
                    event=event,
                    job=job,
                    dry_run=dry_run,
                    verbose=verbose,
                    env_vars=env_vars,
                )

                if retry_result.success:
                    self.logger.info("復旧後の再実行が成功しました")
                    return retry_result
                else:
                    self.logger.warning("復旧後の再実行も失敗しました")

            # 復旧が失敗した場合、フォールバック実行を試行
            if self._auto_recovery.enable_fallback_mode:
                self.logger.info("フォールバック実行を試行します...")
                fallback_result = self._auto_recovery.execute_fallback_mode(
                    workflow_file=workflow_file,
                    job=job,
                    dry_run=True,  # フォールバックは常にドライラン
                    env_vars=env_vars,
                )

                if fallback_result.success:
                    self.logger.info("フォールバック実行が成功しました")
                    # フォールバック結果をDetailedResultに変換
                    return DetailedResult(
                        success=True,
                        returncode=fallback_result.returncode,
                        stdout=fallback_result.stdout,
                        stderr=fallback_result.stderr,
                        command="fallback execution",
                        execution_time_ms=fallback_result.execution_time_ms,
                        trace_id=trace_id,
                    )

        except Exception as e:
            self.logger.error(f"自動復旧中にエラーが発生しました: {e}")

        # すべての復旧試行が失敗した場合、元の結果を返す
        self.logger.error("すべての復旧試行が失敗しました")
        return result

    def get_auto_recovery_statistics(self) -> Dict[str, Any]:
        """
        自動復旧統計を取得

        Returns:
            Dict[str, Any]: 復旧統計情報
        """
        if not self._auto_recovery:
            return {
                "total_sessions": 0,
                "successful_sessions": 0,
                "success_rate": 0.0,
                "auto_recovery_available": False,
            }

        return self._auto_recovery.get_recovery_statistics()

    def _build_act_command(
        self,
        workflow_file: Optional[str] = None,
        event: str | None = None,
        job: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        """
        actコマンドを構築（テスト用）

        Args:
            workflow_file: ワークフローファイル
            event: イベント名
            job: ジョブ名
            dry_run: ドライラン実行
            verbose: 詳細ログ
            env_vars: 環境変数

        Returns:
            List[str]: 構築されたコマンド
        """
        cmd = [self.act_binary]

        if event:
            cmd.append(event)

        if job:
            cmd.extend(["-j", job])

        if workflow_file:
            cmd.extend(["-W", workflow_file])

        if dry_run:
            cmd.append("--dry-run")

        if verbose:
            cmd.append("--verbose")

        if env_vars:
            for key, value in env_vars.items():
                cmd.extend(["--env", f"{key}={value}"])

        return cmd
