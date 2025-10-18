"""
act CLI bridge runner used during Phase 1 migration.

This component invokes the external `act` binary while preserving a
fallback path to the legacy EnhancedActWrapper when the bridge is not yet
fully functional (e.g. `act` が未インストールの場合や未対応機能に遭遇した場合)。
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping

from src.actions.models import SimulationParameters, SimulationResult
from src.actions.path_utils import resolve_workflow_reference

# 標準loggingを使用
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ActBridgeSettings:
    """Configuration container for the act bridge runner."""

    enable_diagnostics: bool = True
    retry_limit: int = 0
    capture_logs: str = "basic"


class ActBridgeRunner:
    """`act` CLI をサブプロセスとして起動する暫定ブリッジ実装。"""

    def __init__(
        self,
        *,
        settings: Mapping[str, Any] | None = None,
    ) -> None:
        self.logger = logger
        self.settings = self._load_settings(settings or {})

    def run(
        self,
        params: SimulationParameters,
    ) -> SimulationResult:
        """
        Execute the target workflow via `act`.

        Raises RuntimeError on failure so that SimulationService can
        transparentlyフォールバック to the legacy wrapper.
        """

        resolution = resolve_workflow_reference(params.workflow_file)

        command = self._build_command(params, act_argument=resolution.act_argument)
        env = self._build_environment(params)
        attempts = 0
        max_attempts = max(1, self.settings.retry_limit + 1)
        self.logger.debug(
            "act bridge command: %s (cwd=%s, attempts=%s)",
            " ".join(shlex.quote(part) for part in command),
            resolution.project_root,
            max_attempts,
        )

        last_stderr = ""
        last_return_code = -1

        while attempts < max_attempts:
            attempts += 1
            start = time.time()
            try:
                completed = subprocess.run(
                    command,
                    cwd=str(resolution.project_root),
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except FileNotFoundError as exc:
                raise RuntimeError("act binary not found; falling back to legacy implementation") from exc

            duration = time.time() - start
            last_stderr = completed.stderr
            last_return_code = completed.returncode

            success = completed.returncode == 0
            self.logger.debug(
                "act bridge attempt %d/%d finished in %.2fs (rc=%d)",
                attempts,
                max_attempts,
                duration,
                completed.returncode,
            )

            if success:
                return self._build_result(
                    params=params,
                    command=command,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                    return_code=completed.returncode,
                    duration_seconds=duration,
                )

            if attempts < max_attempts:
                self.logger.warning(
                    "act bridge attempt %d/%d failed (rc=%d). Retrying...",
                    attempts,
                    max_attempts,
                    completed.returncode,
                )
                continue

        raise RuntimeError(
            f"act bridge failed after {max_attempts} attempt(s) (rc={last_return_code}): {last_stderr.strip()}"
        )

    def _load_settings(self, raw: Mapping[str, Any]) -> ActBridgeSettings:
        """Validate and normalize bridge settings."""
        mutable: MutableMapping[str, Any] = dict(raw)
        capture_mode = str(mutable.get("capture_logs", "basic")).lower()
        if capture_mode not in {"none", "basic", "full"}:
            self.logger.debug("Unknown capture_logs value '%s', defaulting to 'basic'.", capture_mode)
            capture_mode = "basic"
        enable_diagnostics = bool(mutable.get("enable_diagnostics", True))
        retry_limit = self._safe_int(mutable.get("retry_limit", 0))
        if retry_limit < 0:
            self.logger.debug("Negative retry_limit provided; defaulting to 0.")
            retry_limit = 0
        return ActBridgeSettings(
            enable_diagnostics=enable_diagnostics,
            retry_limit=retry_limit,
            capture_logs=capture_mode,
        )

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _build_command(self, params: SimulationParameters, *, act_argument: str) -> list[str]:
        """Construct the `act` CLI command."""
        command: list[str] = ["act", "-W", act_argument]

        if params.job:
            command.extend(["-j", params.job])
        if params.dry_run:
            command.append("--dryrun")
        if params.verbose:
            command.append("--verbose")
        if params.env_file:
            command.extend(["--env-file", str(params.env_file)])

        return command

    def _build_environment(self, params: SimulationParameters) -> dict[str, str]:
        """Merge runtime environment variables."""
        merged_env = os.environ.copy()
        merged_env.setdefault("ACTIONS_USE_ACT_BRIDGE", "1")
        if params.env_vars:
            for key, value in params.env_vars.items():
                merged_env[str(key)] = str(value)
        return merged_env

    def _build_result(
        self,
        *,
        params: SimulationParameters,
        command: list[str],
        stdout: str,
        stderr: str,
        return_code: int,
        duration_seconds: float,
    ) -> SimulationResult:
        metadata: dict[str, Any] = {
            "engine": "act",
            "command": command,
            "duration_seconds": duration_seconds,
            "bridge": True,
        }

        return SimulationResult(
            success=return_code == 0,
            return_code=return_code,
            engine="act",
            stdout=stdout,
            stderr=stderr,
            metadata=metadata,
        )


__all__ = ["ActBridgeRunner", "ActBridgeSettings"]
