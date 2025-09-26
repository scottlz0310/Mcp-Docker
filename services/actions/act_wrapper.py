"""
GitHub Actions Simulator - act wrapper
Configuration-aware integration with the act CLI.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .logger import ActionsLogger


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
                str(container_workdir)
                if isinstance(container_workdir, str)
                else None
            ),
            cache_dir=(
                str(cache_dir)
                if isinstance(cache_dir, str)
                else "/opt/act/cache"
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
    ) -> None:
        self.working_directory = Path(
            working_directory or os.getcwd()
        ).resolve()
        if not self.working_directory.exists():
            raise RuntimeError(
                f"作業ディレクトリが存在しません: {self.working_directory}"
            )
        self.logger = logger or ActionsLogger(verbose=False)
        self.settings = ActRunnerSettings.from_mapping(config)
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
        if self.settings.container_workdir:
            flags.extend(
                ["--container-workdir", self.settings.container_workdir]
            )
        if self.settings.image:
            platforms = self.settings.platforms or ("ubuntu-latest",)
            for platform in platforms:
                flags.extend(["-P", f"{platform}={self.settings.image}"])
        elif self.settings.platforms:
            for platform in self.settings.platforms:
                flags.extend(["--platform", platform])
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
        if self.settings.cache_dir:
            env.setdefault("ACT_CACHE_DIR", self.settings.cache_dir)
        if default_event and "GITHUB_EVENT_NAME" not in env:
            env["GITHUB_EVENT_NAME"] = default_event
        if overrides:
            env.update({str(k): str(v) for k, v in overrides.items()})
        return env

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

        try:
            result = subprocess.run(
                cmd,
                cwd=self.working_directory,
                capture_output=True,
                text=True,
                timeout=600,
                env=process_env,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self.logger.error("actの実行がタイムアウトしました")
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Execution timeout",
                "command": " ".join(cmd),
            }
        except (OSError, subprocess.SubprocessError) as exc:
            self.logger.error(f"act実行エラー: {exc}")
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(exc),
                "command": " ".join(cmd),
            }

        if result.returncode != 0:
            self.logger.error(
                f"act 実行が失敗しました (returncode={result.returncode})"
            )

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(cmd),
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
