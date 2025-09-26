#!/usr/bin/env python3
"""tests for the SimulationService abstraction."""

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


class DummySimulator:
    """Fake simulator used to isolate builtin engine tests."""

    def __init__(self, logger: ActionsLogger | None = None) -> None:
        self.logger = logger or ActionsLogger(verbose=False)
        self.env_vars: dict[str, Any] = {}
        self.loaded_env_files: list[Path] = []

    def load_env_file(self, env_file: Path) -> None:
        self.loaded_env_files.append(env_file)

    def run(
        self,
        workflow: dict[str, Any],
        job_name: str | None = None,
    ) -> int:
        return 0

    def dry_run(
        self,
        workflow: dict[str, Any],
        job_name: str | None = None,
    ) -> int:
        return 0


class DummyParser:
    """Fake workflow parser for builtin engine tests."""

    def __init__(self, workflow: dict[str, Any]) -> None:
        self._workflow = workflow

    def parse_file(self, file_path: Path) -> dict[str, Any]:
        if not file_path.exists():
            raise AssertionError("Expected workflow file to exist")
        return self._workflow


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


def test_builtin_engine_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    logger: ActionsLogger,
) -> None:
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text("name: test\njobs: {}\n", encoding="utf-8")

    fake_workflow: dict[str, Any] = {"jobs": {}}

    monkeypatch.setattr(
        "services.actions.service.WorkflowParser",
        lambda: DummyParser(fake_workflow),
    )
    monkeypatch.setattr(
        "services.actions.service.WorkflowSimulator",
        DummySimulator,
    )

    service = SimulationService()
    params = SimulationParameters(
        workflow_file=workflow_file,
        engine="builtin",
        dry_run=False,
        verbose=False,
    )

    result = service.run_simulation(params, logger=logger)

    assert result.success is True
    assert result.engine == "builtin"
    assert result.return_code == 0


def test_act_engine_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    logger: ActionsLogger,
) -> None:
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text("name: act\njobs: {}\n", encoding="utf-8")

    wrapper = DummyActWrapper(success=True)
    monkeypatch.setattr(
        "services.actions.service.ActWrapper",
        wrapper,
    )

    service = SimulationService()
    params = SimulationParameters(
        workflow_file=workflow_file,
        engine="act",
        dry_run=True,
        verbose=False,
    )

    result = service.run_simulation(params, logger=logger)

    assert result.success is True
    assert result.engine == "act"
    assert result.return_code == 0
    assert result.metadata["command"] == "act"
    assert wrapper.calls, "ActWrapper.run_workflow should have been called"


def test_act_engine_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    logger: ActionsLogger,
) -> None:
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text("name: act\njobs: {}\n", encoding="utf-8")

    def raise_runtime_error(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("act binary not found")

    monkeypatch.setattr(
        "services.actions.service.ActWrapper",
        raise_runtime_error,
    )

    service = SimulationService()
    params = SimulationParameters(
        workflow_file=workflow_file,
        engine="act",
        dry_run=False,
        verbose=False,
    )

    with pytest.raises(SimulationServiceError) as exc:
        service.run_simulation(params, logger=logger)

    assert "act binary not found" in str(exc.value)


def test_unknown_engine(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    logger: ActionsLogger,
) -> None:
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text("name: test\njobs: {}\n", encoding="utf-8")

    service = SimulationService()
    params = SimulationParameters(
        workflow_file=workflow_file,
        engine="invalid",
        dry_run=False,
        verbose=False,
    )

    with pytest.raises(SimulationServiceError):
        service.run_simulation(params, logger=logger)
