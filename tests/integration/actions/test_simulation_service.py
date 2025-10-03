#!/usr/bin/env python3
"""Tests for the act-backed ``SimulationService`` abstraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from services.actions.logger import ActionsLogger
from services.actions.service import (
    SimulationParameters,
    SimulationService,
    SimulationServiceError,
)


class DummyActWrapper:
    """Fake act wrapper used to simulate external command execution."""

    def __init__(self, *, success: bool = True) -> None:
        self.success = success
        self.calls: list[dict[str, Any]] = []

    def __call__(self, working_directory: str) -> DummyActWrapper:
        self.working_directory = working_directory
        return self

    def run_workflow(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {
            "success": self.success,
            "returncode": 0 if self.success else 1,
            "stdout": "ok" if self.success else "",
            "stderr": "" if self.success else "error",
            "command": "act",
        }


@pytest.fixture()
def logger() -> ActionsLogger:
    return ActionsLogger(verbose=False)


def test_run_simulation_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    logger: ActionsLogger,
) -> None:
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text("name: test\njobs: {}\n", encoding="utf-8")

    wrapper = DummyActWrapper(success=True)
    monkeypatch.setattr("services.actions.service.ActWrapper", wrapper)

    service = SimulationService()
    params = SimulationParameters(
        workflow_file=workflow_file,
        dry_run=True,
        verbose=False,
    )

    result = service.run_simulation(params, logger=logger)

    assert result.success is True
    assert result.engine == "act"
    assert result.return_code == 0
    assert result.metadata["command"] == "act"
    assert wrapper.calls, "ActWrapper.run_workflow should have been called"


def test_run_simulation_merges_env_vars(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    logger: ActionsLogger,
) -> None:
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text("name: test\njobs: {}\n", encoding="utf-8")

    env_file = tmp_path / ".env"
    env_file.write_text("FOO=bar\n", encoding="utf-8")

    wrapper = DummyActWrapper(success=True)
    monkeypatch.setattr("services.actions.service.ActWrapper", wrapper)

    service = SimulationService()
    params = SimulationParameters(
        workflow_file=workflow_file,
        dry_run=False,
        env_file=env_file,
        env_vars={"BAZ": "qux"},
        verbose=False,
    )

    service.run_simulation(params, logger=logger)

    assert wrapper.calls, "ActWrapper.run_workflow should have been called"
    env_vars = wrapper.calls[0]["env_vars"]
    assert env_vars == {"FOO": "bar", "BAZ": "qux"}


def test_run_simulation_missing_workflow(
    tmp_path: Path,
    logger: ActionsLogger,
) -> None:
    workflow_file = tmp_path / "missing.yml"

    service = SimulationService()
    params = SimulationParameters(
        workflow_file=workflow_file,
        dry_run=False,
        verbose=False,
    )

    with pytest.raises(SimulationServiceError) as exc:
        service.run_simulation(params, logger=logger)

    assert "ワークフローファイルが見つかりません" in str(exc.value)


def test_run_simulation_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    logger: ActionsLogger,
) -> None:
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text("name: test\njobs: {}\n", encoding="utf-8")

    def raise_runtime_error(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("act binary not found")

    monkeypatch.setattr(
        "services.actions.service.ActWrapper",
        raise_runtime_error,
    )

    service = SimulationService()
    params = SimulationParameters(
        workflow_file=workflow_file,
        dry_run=False,
        verbose=False,
    )

    with pytest.raises(SimulationServiceError) as exc:
        service.run_simulation(params, logger=logger)

    assert "act binary not found" in str(exc.value)
