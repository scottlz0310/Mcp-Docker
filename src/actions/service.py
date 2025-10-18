"""High-level simulation service shared by CLI and API layers."""

from __future__ import annotations

import logging
import os
import time
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
from typing import TYPE_CHECKING, Any, Mapping

from .models import SimulationParameters, SimulationResult

if TYPE_CHECKING:
    from .act_bridge import ActBridgeRunner


class SimulationServiceError(Exception):
    """Raised when the simulation service fails to execute a request."""


class SimulationService:
    """Execute workflow simulations via the act CLI."""

    def __init__(
        self,
        config: Mapping[str, Any] | None = None,
        use_act_bridge: bool | None = None,
        act_bridge_config: Mapping[str, Any] | None = None,
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self._config: dict[str, Any] = dict(config) if config else {}
        self._use_act_bridge = self._resolve_use_act_bridge(use_act_bridge)
        self._act_bridge_config: dict[str, Any] = dict(act_bridge_config) if act_bridge_config else {}
        self._act_bridge_runner: "ActBridgeRunner | None" = None

        if self._use_act_bridge:
            from .act_bridge import ActBridgeRunner  # local import to avoid cycle

            self._act_bridge_runner = ActBridgeRunner(settings=self._act_bridge_config)

    @staticmethod
    def _resolve_use_act_bridge(flag: bool | None) -> bool:
        if flag is not None:
            return flag
        env_value = os.getenv("ACTIONS_USE_ACT_BRIDGE")
        if env_value is None:
            return False
        return env_value.strip().lower() in {"1", "true", "yes", "on"}

    def set_config(self, config: Mapping[str, Any] | None) -> None:
        self._config = dict(config) if config else {}

    def run_simulation(
        self,
        params: SimulationParameters,
        *,
        capture_output: bool = False,
    ) -> SimulationResult:
        """Run the workflow simulation and return a structured result."""
        if self._use_act_bridge and self._act_bridge_runner:
            self._logger.info("act bridge モードを使用します")
            try:
                return self._act_bridge_runner.run(params)
            except NotImplementedError as exc:
                self._logger.debug(f"Act bridge runner は未実装: {exc}")
            except Exception as exc:
                self._logger.warning(f"Act bridge runner の実行に失敗: {exc}")

        stdout_io: StringIO | None = None
        stderr_io: StringIO | None = None

        try:
            with ExitStack() as stack:
                if capture_output:
                    stdout_io = StringIO()
                    stderr_io = StringIO()
                    stack.enter_context(redirect_stdout(stdout_io))
                    stack.enter_context(redirect_stderr(stderr_io))

                try:
                    result = self._run_with_act(params)
                except SimulationServiceError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    raise SimulationServiceError(f"Unexpected error: {exc}") from exc

            if capture_output:
                extra_stdout = stdout_io.getvalue() if stdout_io else ""
                extra_stderr = stderr_io.getvalue() if stderr_io else ""
                if extra_stdout:
                    result.stdout = f"{extra_stdout}{result.stdout}"
                if extra_stderr:
                    result.stderr = f"{extra_stderr}{result.stderr}"

            return result

        finally:
            pass

    def _run_with_act(
        self,
        params: SimulationParameters,
    ) -> SimulationResult:
        # 簡易実装: act_bridgeに委譲
        raise SimulationServiceError("Legacy wrapper removed. Use act_bridge instead.")

    def get_simulation_status(self) -> dict[str, Any]:
        """シミュレーションサービスの現在の状態を取得"""
        return {
            "service_initialized": True,
            "act_bridge_enabled": self._use_act_bridge,
            "config_keys": list(self._config.keys()) if self._config else [],
            "timestamp": time.time(),
        }
