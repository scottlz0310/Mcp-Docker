"""Shared data models for the actions simulation service."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SimulationParameters:
    """Parameters that control a single simulation run."""

    workflow_file: Path
    job: str | None = None
    dry_run: bool = False
    env_file: Path | None = None
    env_vars: dict[str, str] | None = None
    verbose: bool = False


@dataclass(slots=True)
class SimulationResult:
    """Structured output returned by the simulation service."""

    success: bool
    return_code: int
    engine: str = "act"
    stdout: str = ""
    stderr: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = ["SimulationParameters", "SimulationResult"]
