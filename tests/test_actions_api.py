#!/usr/bin/env python3
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""FastAPI layer tests for the actions simulation service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from services.actions.api import create_app, get_simulation_service
from services.actions.service import SimulationResult, SimulationServiceError


class DummySimulationService:
    """Stubbed simulation service for API tests."""

    def __init__(
        self,
        *,
        result: SimulationResult | None = None,
        raise_error: bool = False,
    ) -> None:
        self.result = result
        self.raise_error = raise_error
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def run_simulation(self, *args: Any, **kwargs: Any) -> SimulationResult:
        self.calls.append((args, kwargs))
        if self.raise_error:
            raise SimulationServiceError("simulation failed")
        if self.result is None:
            raise AssertionError(
                "DummySimulationService requires a result when raise_error=False",
            )
        return self.result


def make_client(
    override: DummySimulationService | None = None,
) -> TestClient:
    """Construct a TestClient, optionally overriding the simulation service."""

    app = create_app()
    if override is not None:
        app.dependency_overrides[get_simulation_service] = lambda: override
    return TestClient(app)


def test_healthz_endpoint() -> None:
    client = make_client()
    response = client.get("/actions/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_simulate_success(tmp_path: Path) -> None:
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text("name: test\njobs: {}\n", encoding="utf-8")

    dummy_result = SimulationResult(
        success=True,
        return_code=0,
        engine="builtin",
        stdout="ok",
        stderr="",
        metadata={"source": "dummy"},
    )
    service = DummySimulationService(result=dummy_result)
    client = make_client(service)

    payload: dict[str, Any] = {
        "workflow_file": str(workflow_file),
        "engine": "builtin",
        "dry_run": False,
        "verbose": False,
    }

    response = client.post("/actions/simulate", json=payload)

    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert body["success"] is True
    assert body["return_code"] == 0
    assert body["engine"] == "builtin"
    assert body["stdout"] == "ok"
    assert body["metadata"] == {"source": "dummy"}
    assert service.calls, "Simulation service should have been invoked"


def test_simulate_service_error(tmp_path: Path) -> None:
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text("name: test\njobs: {}\n", encoding="utf-8")

    service = DummySimulationService(raise_error=True)
    client = make_client(service)

    payload: dict[str, Any] = {
        "workflow_file": str(workflow_file),
        "engine": "builtin",
    }

    response = client.post("/actions/simulate", json=payload)

    assert response.status_code == 400
    assert "simulation failed" in response.json()["detail"]


def test_simulate_missing_file(tmp_path: Path) -> None:
    dummy_result = SimulationResult(
        success=True,
        return_code=0,
        engine="builtin",
        stdout="",
        stderr="",
        metadata={},
    )
    service = DummySimulationService(result=dummy_result)
    client = make_client(service)

    missing_file = tmp_path / "missing.yml"
    payload: dict[str, Any] = {
        "workflow_file": str(missing_file),
        "engine": "builtin",
    }

    response = client.post("/actions/simulate", json=payload)

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "workflow file not found" in detail
    assert not service.calls, "Service should not be invoked when file is missing"
