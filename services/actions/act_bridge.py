"""
Skeleton implementation for the upcoming act bridge runner.

This module provides placeholder types that will be fleshed out during
Phase 1 of the migration project. For now it only validates configuration
and surfaces a clear message when the bridge is invoked.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, MutableMapping

from .logger import ActionsLogger

if TYPE_CHECKING:
    from .service import SimulationParameters, SimulationResult


@dataclass(frozen=True)
class ActBridgeSettings:
    """Configuration container for the act bridge runner."""

    enable_diagnostics: bool = True
    retry_limit: int = 0
    capture_logs: str = "basic"


class ActBridgeRunner:
    """
    Placeholder runner that will eventually execute workflows through act.

    The current implementation only prepares configuration and raises a
    descriptive error when invoked.
    """

    def __init__(
        self,
        *,
        settings: Mapping[str, Any] | None = None,
        logger: ActionsLogger | None = None,
    ) -> None:
        self.logger = logger or ActionsLogger(verbose=False)
        self.settings = self._load_settings(settings or {})

    def run(
        self,
        params: "SimulationParameters",
        *,
        logger: ActionsLogger | None = None,
    ) -> "SimulationResult":
        raise NotImplementedError(
            "ActBridgeRunner is a skeleton implementation. Execution support will be added in Phase 1."
        )

    def _load_settings(self, raw: Mapping[str, Any]) -> ActBridgeSettings:
        """Validate and normalize bridge settings."""
        mutable: MutableMapping[str, Any] = dict(raw)
        capture_mode = str(mutable.get("capture_logs", "basic")).lower()
        if capture_mode not in {"none", "basic", "full"}:
            self.logger.debug(f"Unknown capture_logs value '{capture_mode}', defaulting to 'basic'.")
            capture_mode = "basic"
        enable_diagnostics = bool(mutable.get("enable_diagnostics", True))
        try:
            retry_limit = int(mutable.get("retry_limit", 0))
        except (TypeError, ValueError):
            self.logger.debug("Invalid retry_limit value; defaulting to 0.")
            retry_limit = 0
        if retry_limit < 0:
            self.logger.debug("Negative retry_limit provided; defaulting to 0.")
            retry_limit = 0
        return ActBridgeSettings(
            enable_diagnostics=enable_diagnostics,
            retry_limit=retry_limit,
            capture_logs=capture_mode,
        )


__all__ = ["ActBridgeRunner", "ActBridgeSettings"]
