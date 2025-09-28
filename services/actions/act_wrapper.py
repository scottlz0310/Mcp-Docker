"""
GitHub Actions Simulator - act wrapper
Configuration-aware integration with the act CLI.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, cast

from .logger import ActionsLogger
from .execution_tracer import ExecutionTracer, ExecutionStage, ThreadState

try:
    import yaml  # type: ignore[import-untyped]
except ModuleNotFoundError as exc:  # pragma: no cover - defensive
    raise RuntimeError("PyYAML がインストールされていません") from exc


@dataclass(frozen=True)
class ActRunnerSettings:
    """Settings resolved from configuration for act execution."""

    image: str | None = None
    platforms: tuple[str, ...] = field(default_factory=tuple)
    container_workdir: str | None = None
    cache_dir: str | None = "/opt/act/cache"
    env: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_mapping(
        cls,
        config: Mapping[str, Any] | None,
    ) -> "ActRunnerSettings":
        if not isinstance(config, Mapping):
            return cls()

        runner_cfg_raw = config.get("runner", {})
        if not isinstance(runner_cfg_raw, Mapping):
            runner_cfg_raw = {}
        runner_cfg: Dict[str, Any] = {
            str(key): value for key, value in runner_cfg_raw.items()
        }

        env_cfg_raw = config.get("environment", {})
        if not isinstance(env_cfg_raw, Mapping):
            env_cfg_raw = {}
        env_cfg: Dict[str, Any] = {
            str(key): value for key, value in env_cfg_raw.items()
        }

        image = runner_cfg.get("image")
        platforms_value = runner_cfg.get("platforms", ())
        platforms_list: List[str]
        if isinstance(platforms_value, str):
            platforms_list = [platforms_value]
        elif isinstance(platforms_value, Iterable):
            platforms_list = [str(item) for item in platforms_value]
        else:
            platforms_list = []
        platforms = tuple(platforms_list)

        container_workdir = runner_cfg.get("container_workdir")
        cache_dir = runner_cfg.get("cache_dir")

        resolved_env = {str(key): str(value) for key, value in env_cfg.items()}

        return cls(
            image=str(image) if isinstance(image, str) else None,
            platforms=platforms,
            container_workdir=(
                str(container_workdir) if isinstance(container_workdir, str) else None
            ),
            cache_dir=(
                str(cache_dir) if isinstance(cache_dir, str) else "/opt/act/cache"
            ),
            env=resolved_env,
        )


class ActWrapper:
    """nektos/act CLI integration with configuration support."""

    def __init__(
        self,
        working_directory: Optional[str] = None,
        *,
        config: Mapping[str, Any] | None = None,
        logger: ActionsLogger | None = None,
        execution_tracer: Optional[ExecutionTracer] = None,
    ) -> None:
        self.working_directory = Path(working_directory or os.getcwd()).resolve()
        if not self.working_directory.exists():
            raise RuntimeError(
                f"作業ディレクトリが存在しません: {self.working_directory}"
            )
        self.logger = logger or ActionsLogger(verbose=False)
        self.execution_tracer = execution_tracer or ExecutionTracer(logger=self.logger)
        self.settings = ActRunnerSettings.from_mapping(config)
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

    def _find_act_binary(self) -> str:
        """Locate the act binary in the current environment."""

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

    def _compose_runner_flags(self) -> list[str]:
        flags: list[str] = []

        # 非対話的実行を強制するフラグを追加（quietは削除して出力を表示）
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
        env = os.environ.copy()

        # 非対話的実行を強制する環境変数を設定
        env["ACT_LOG_LEVEL"] = "info"
        env["ACT_PLATFORM"] = "ubuntu-latest=catthehacker/ubuntu:act-latest"
        env["DOCKER_HOST"] = "unix:///var/run/docker.sock"

        if self.settings.cache_dir:
            env.setdefault("ACT_CACHE_DIR", self.settings.cache_dir)
        if default_event and "GITHUB_EVENT_NAME" not in env:
            env["GITHUB_EVENT_NAME"] = default_event
        if overrides:
            env.update({str(k): str(v) for k, v in overrides.items()})
        return env

    def _resolve_timeout_seconds(
        self,
        config: Mapping[str, Any] | None,
    ) -> int:
        default_timeout = 600
        timeout_value = default_timeout

        if isinstance(config, Mapping):
            timeouts_section = config.get("timeouts")
            if isinstance(timeouts_section, Mapping):
                candidate = timeouts_section.get("act_seconds")
                parsed = self._coerce_timeout(candidate, "configuration")
                if parsed is not None:
                    timeout_value = parsed

        env_candidate = os.getenv("ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS")
        parsed_env = self._coerce_timeout(
            env_candidate,
            "ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS",
        )
        if parsed_env is not None:
            timeout_value = parsed_env

        return timeout_value

    def _coerce_timeout(
        self,
        raw_value: Any,
        source: str,
    ) -> int | None:
        if raw_value is None:
            return None

        try:
            if isinstance(raw_value, (int, float)):
                seconds = int(raw_value)
            else:
                seconds = int(float(str(raw_value).strip()))
        except (ValueError, TypeError):
            self.logger.warning(
                f"無効なタイムアウト値を無視します ({source}): {raw_value}",
            )
            return None

        if seconds <= 0:
            self.logger.warning(
                f"タイムアウト値は正の秒数である必要があります ({source}): {raw_value}",
            )
            return None

        return seconds

    def list_workflows(self) -> list[Dict[str, Any]]:
        """Return available workflows/jobs from act."""

        cmd = [self.act_binary, "--list", "--json"]
        cmd.extend(self._compose_runner_flags())

        try:
            result = subprocess.run(
                cmd,
                cwd=self.working_directory,
                capture_output=True,
                text=True,
                check=True,
                env=self._build_process_env(None, None),
            )
        except subprocess.CalledProcessError as exc:
            self.logger.error(f"actワークフロー一覧取得エラー: {exc.stderr.strip()}")
            return []

        workflows: list[Dict[str, Any]] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            try:
                workflows.append(json.loads(line))
            except json.JSONDecodeError:
                self.logger.warning(f"JSONの解析に失敗: {line}")
        return workflows

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

        # 実行トレースを開始
        trace_id = f"act_workflow_{int(time.time() * 1000)}"
        self.execution_tracer.start_trace(trace_id)

        try:
            # 初期化段階
            self.execution_tracer.set_stage(
                ExecutionStage.INITIALIZATION,
                {
                    "workflow_file": workflow_file,
                    "job": job,
                    "dry_run": dry_run,
                    "verbose": verbose,
                    "mock_mode": self._mock_mode,
                },
            )

            if self._mock_mode:
                result = self._run_mock_workflow(
                    workflow_file=workflow_file,
                    job=job,
                    dry_run=dry_run,
                    verbose=verbose,
                    env_vars=env_vars,
                )
                self.execution_tracer.set_stage(ExecutionStage.COMPLETED)
                return result

            cmd: list[str] = [self.act_binary]
            cmd.extend(self._compose_runner_flags())

            if workflow_file:
                cmd.extend(["-W", workflow_file])
            if job:
                cmd.extend(["-j", job])
            if dry_run:
                cmd.append("--dryrun")
            if verbose:
                cmd.append("--verbose")

            env_args = self._compose_env_args(env_vars)
            cmd.extend(env_args)

            process_env = self._build_process_env(event or None, env_vars)

            self.logger.info(f"actコマンド実行: {' '.join(cmd)}")

            # Docker通信監視を開始
            docker_op = self.execution_tracer.monitor_docker_communication(
                operation_type="act_execution", command=cmd
            )

            stdout_lines: list[str] = []
            stderr_lines: list[str] = []

            def _stream_output(
                pipe: Any,
                collector: list[str],
                label: str,
                thread_trace,
            ) -> None:
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
                            if not line:
                                continue
                            # 常に出力を表示（デバッグ用）
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

            # サブプロセス作成段階
            self.execution_tracer.set_stage(ExecutionStage.SUBPROCESS_CREATION)

            try:
                process = subprocess.Popen(
                    cmd,
                    cwd=self.working_directory,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=process_env,
                )
                self.logger.info(f"actプロセス開始: PID={process.pid}")
            except (OSError, subprocess.SubprocessError) as exc:
                self.logger.error(f"act実行エラー: {exc}")
                self.execution_tracer.update_docker_operation(
                    docker_op, success=False, error_message=str(exc)
                )
                self.execution_tracer.set_stage(ExecutionStage.FAILED)
                return {
                    "success": False,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": str(exc),
                    "command": " ".join(cmd),
                }

            # プロセストレースを開始
            process_trace = self.execution_tracer.trace_subprocess_execution(
                cmd, process, str(self.working_directory)
            )

            # 出力ストリーミング段階
            self.execution_tracer.set_stage(ExecutionStage.OUTPUT_STREAMING)

            threads: list[threading.Thread] = []
            thread_traces = []

            if process.stdout:
                t_out = threading.Thread(
                    target=_stream_output,
                    args=(process.stdout, stdout_lines, "act stdout", None),
                    daemon=True,
                    name="ActWrapper-StdoutStream",
                )
                thread_trace_out = self.execution_tracer.track_thread_lifecycle(
                    t_out, "_stream_output"
                )
                # スレッド関数の引数を更新
                t_out = threading.Thread(
                    target=_stream_output,
                    args=(process.stdout, stdout_lines, "act stdout", thread_trace_out),
                    daemon=True,
                    name="ActWrapper-StdoutStream",
                )
                t_out.start()
                threads.append(t_out)
                thread_traces.append(thread_trace_out)

            if process.stderr:
                t_err = threading.Thread(
                    target=_stream_output,
                    args=(process.stderr, stderr_lines, "act stderr", None),
                    daemon=True,
                    name="ActWrapper-StderrStream",
                )
                thread_trace_err = self.execution_tracer.track_thread_lifecycle(
                    t_err, "_stream_output"
                )
                # スレッド関数の引数を更新
                t_err = threading.Thread(
                    target=_stream_output,
                    args=(process.stderr, stderr_lines, "act stderr", thread_trace_err),
                    daemon=True,
                    name="ActWrapper-StderrStream",
                )
                t_err.start()
                threads.append(t_err)
                thread_traces.append(thread_trace_err)

            # プロセス監視段階
            self.execution_tracer.set_stage(ExecutionStage.PROCESS_MONITORING)

            start_time = time.time()
            heartbeat_interval = 30
            next_heartbeat = start_time + heartbeat_interval
            deadline = (
                start_time + self._timeout_seconds if self._timeout_seconds else None
            )
            timed_out = False

            while True:
                return_code = process.poll()
                if return_code is not None:
                    break

                now = time.time()
                if deadline and now >= deadline:
                    timed_out = True
                    self.logger.error("actの実行がタイムアウトしました")

                    # ハングアップ検出
                    hang_info = self.execution_tracer.detect_hang_condition(
                        self._timeout_seconds
                    )
                    if hang_info:
                        self.logger.error(f"ハングアップを検出: {hang_info}")

                    process.kill()
                    self.execution_tracer.set_stage(ExecutionStage.TIMEOUT)
                    break

                if now >= next_heartbeat:
                    elapsed = int(now - start_time)

                    # ハートビートログを記録
                    process_info = {
                        "pid": process.pid,
                        "elapsed_seconds": elapsed,
                        "return_code": process.poll(),
                    }
                    self.execution_tracer.log_heartbeat(
                        f"act 実行中... {elapsed} 秒経過 (PID: {process.pid})",
                        process_info,
                    )

                    next_heartbeat = now + heartbeat_interval

                time.sleep(1)

            if process.poll() is None:
                process.wait()

            # クリーンアップ段階
            self.execution_tracer.set_stage(ExecutionStage.CLEANUP)

            for thread in threads:
                thread.join(timeout=2)

            stdout_text = "".join(stdout_lines)
            stderr_text = "".join(stderr_lines)

            # プロセストレースを更新
            self.execution_tracer.update_process_trace(
                process_trace,
                return_code=process.returncode,
                stdout_bytes=len(stdout_text.encode("utf-8")),
                stderr_bytes=len(stderr_text.encode("utf-8")),
                error_message="Execution timeout" if timed_out else None,
            )

            # Docker操作を更新
            self.execution_tracer.update_docker_operation(
                docker_op,
                success=not timed_out and (process.returncode == 0),
                return_code=process.returncode,
                stdout=stdout_text[:1000],  # 最初の1000文字のみ保存
                stderr=stderr_text[:1000],
                error_message="Execution timeout" if timed_out else None,
            )

            if timed_out:
                self.execution_tracer.set_stage(ExecutionStage.TIMEOUT)
                return {
                    "success": False,
                    "returncode": -1,
                    "stdout": stdout_text,
                    "stderr": stderr_text or "Execution timeout",
                    "command": " ".join(cmd),
                }

            exit_code = process.returncode or 0

            if exit_code != 0:
                self.logger.error(f"act 実行が失敗しました (returncode={exit_code})")
                self.execution_tracer.set_stage(ExecutionStage.FAILED)
            else:
                self.execution_tracer.set_stage(ExecutionStage.COMPLETED)

            return {
                "success": exit_code == 0,
                "returncode": exit_code,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "command": " ".join(cmd),
            }

        finally:
            # トレースを終了
            final_trace = self.execution_tracer.end_trace()
            if final_trace and self.logger.verbose:
                self.logger.debug(
                    f"実行トレース完了: {final_trace.trace_id}, 実行時間: {final_trace.duration_ms:.2f}ms"
                )

    def _run_mock_workflow(
        self,
        *,
        workflow_file: Optional[str],
        job: Optional[str],
        dry_run: bool,
        verbose: bool,
        env_vars: Optional[Dict[str, str]],
    ) -> Dict[str, Any]:
        workflow_name = workflow_file or "workflow.yml"
        workflow_path = (self.working_directory / workflow_name).resolve()

        if not workflow_path.exists():
            message = f"ワークフローファイルが見つかりません: {workflow_path}"
            self.logger.error(message)
            return {
                "success": False,
                "returncode": 1,
                "stdout": "",
                "stderr": message,
                "command": f"mock-act -W {workflow_name}",
            }

        try:
            with workflow_path.open("r", encoding="utf-8") as handle:
                workflow_raw: Any = yaml.safe_load(handle) or {}
        except (
            OSError,
            yaml.YAMLError,
        ) as exc:  # pragma: no cover - defensive
            message = f"ワークフローファイルの読み込みに失敗しました: {exc}"
            self.logger.error(message)
            return {
                "success": False,
                "returncode": 1,
                "stdout": "",
                "stderr": message,
                "command": f"mock-act -W {workflow_name}",
            }

        workflow_data: dict[str, Any] = {}
        if isinstance(workflow_raw, Mapping):
            workflow_map = cast(Mapping[Any, Any], workflow_raw)
            for key, value in workflow_map.items():
                workflow_data[str(key)] = value

        jobs_data: dict[str, dict[str, Any]] = {}
        jobs_raw = workflow_data.get("jobs")
        if isinstance(jobs_raw, Mapping):
            jobs_map = cast(Mapping[Any, Any], jobs_raw)
            for job_key, job_value in jobs_map.items():
                job_id_str = str(job_key)
                if isinstance(job_value, Mapping):
                    job_details_map = cast(Mapping[Any, Any], job_value)
                    jobs_data[job_id_str] = {
                        str(step_key): step_value
                        for step_key, step_value in job_details_map.items()
                    }
                else:
                    jobs_data[job_id_str] = {}

        if job and job not in jobs_data:
            message = "指定されたジョブが見つかりません"
            self.logger.error(message)
            return {
                "success": False,
                "returncode": 1,
                "stdout": "",
                "stderr": message,
                "command": f"mock-act -W {workflow_name} -j {job}",
            }

        selected_jobs: list[tuple[str, dict[str, Any]]] = []
        if job:
            selected_jobs.append((job, jobs_data.get(job, {})))
        else:
            selected_jobs.extend(jobs_data.items())

        if self._mock_delay_seconds:
            time.sleep(self._mock_delay_seconds)

        workflow_name_raw = workflow_data.get("name")
        workflow_display = (
            str(workflow_name_raw)
            if isinstance(workflow_name_raw, str)
            else workflow_name
        )
        lines: list[str] = []
        if dry_run:
            lines.append(f"ドライラン実行: {workflow_display}")
        else:
            lines.append(f"シミュレーション実行: {workflow_display}")

        if selected_jobs:
            for job_id, job_def in selected_jobs:
                job_title_raw = job_def.get("name")
                display_name = (
                    str(job_title_raw) if isinstance(job_title_raw, str) else job_id
                )
                lines.append(f"ジョブ: {display_name}")
                if verbose:
                    lines.append(f"  - job_id={job_id}")
        else:
            lines.append("ジョブが定義されていません")

        if env_vars:
            lines.append("環境変数:")
            for key, value in sorted(env_vars.items()):
                lines.append(f"  - {key}={value}")

        stdout_text = "\n".join(lines) + "\n"

        return {
            "success": True,
            "returncode": 0,
            "stdout": stdout_text,
            "stderr": "",
            "command": f"mock-act -W {workflow_name}",
        }

    def validate_workflow(self, workflow_file: str) -> Dict[str, Any]:
        """Run act in dry-run mode for validation purposes."""

        return self.run_workflow(
            workflow_file=workflow_file,
            dry_run=True,
            verbose=True,
        )

    def get_workflow_jobs(self, workflow_file: str) -> list[Dict[str, Any]]:
        """Return job metadata for a specific workflow file."""

        cmd = [self.act_binary, "--list", "-W", workflow_file]
        cmd.extend(self._compose_runner_flags())

        try:
            result = subprocess.run(
                cmd,
                cwd=self.working_directory,
                capture_output=True,
                text=True,
                check=True,
                env=self._build_process_env(None, None),
            )
        except subprocess.CalledProcessError as exc:
            self.logger.error(f"ワークフロージョブ取得エラー: {exc.stderr.strip()}")
            return []

        jobs: list[Dict[str, Any]] = []
        lines = result.stdout.strip().splitlines()
        for line in lines[1:]:  # skip header line
            parts = line.split()
            if len(parts) < 6:
                continue
            jobs.append(
                {
                    "stage": parts[0],
                    "job_id": parts[1],
                    "job_name": parts[2],
                    "workflow_name": " ".join(parts[3:-2]),
                    "workflow_file": parts[-2],
                    "events": parts[-1],
                }
            )
        return jobs

    def check_requirements(self) -> Dict[str, Any]:
        """Check whether the environment satisfies act prerequisites."""

        issues: List[str] = []
        requirements: Dict[str, Any] = {
            "act_binary": bool(self.act_binary),
            "docker": False,
            "docker_running": False,
            "version": None,
            "issues": issues,
        }

        if not self.act_binary:
            issues.append("actバイナリが見つかりません")

        if shutil.which("docker"):
            try:
                docker_version = subprocess.run(
                    ["docker", "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                requirements["docker"] = True
                requirements["docker_version"] = docker_version.stdout.strip()
            except subprocess.CalledProcessError:
                issues.append("Dockerが正しくインストールされていません")

            try:
                subprocess.run(
                    ["docker", "info"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                requirements["docker_running"] = True
            except subprocess.CalledProcessError:
                issues.append("Dockerデーモンが実行されていません")
        else:
            issues.append("Dockerがインストールされていません")

        try:
            act_version = subprocess.run(
                [self.act_binary, "--version"],
                capture_output=True,
                text=True,
                check=True,
                env=self._build_process_env(None, None),
            )
            requirements["version"] = act_version.stdout.strip()
        except subprocess.CalledProcessError:
            issues.append("actバージョンの取得に失敗しました")

        return requirements
