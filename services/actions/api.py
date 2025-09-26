# pyright: reportUnusedFunction=false
"""FastAPI application exposing the Actions simulation service."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from .logger import ActionsLogger
from .service import (
    SimulationParameters,
    SimulationResult,
    SimulationService,
    SimulationServiceError,
)


class SimulateRequest(BaseModel):
    """Request body for workflow simulation."""

    workflow_file: str = Field(
        ...,
        description="Path to the workflow file on the server",
    )
    job: str | None = Field(
        default=None,
        description="Optional job name to run",
    )
    dry_run: bool = Field(
        default=False,
        description="If true, performs a dry run",
    )
    env_file: str | None = Field(
        default=None,
        description="Optional path to an env file containing key=value pairs",
    )
    env_vars: dict[str, str] | None = Field(
        default=None,
        description="Additional environment variables to inject",
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose logging",
    )


class SimulateResponse(BaseModel):
    """Response payload returned after executing a simulation."""

    success: bool
    return_code: int
    engine: str
    stdout: str
    stderr: str
    metadata: dict[str, object]


_SERVICE = SimulationService()


def get_simulation_service() -> SimulationService:
    """Return the shared SimulationService instance."""

    return _SERVICE


def _build_parameters(payload: SimulateRequest) -> SimulationParameters:
    """Convert the request model into SimulationParameters."""

    workflow_path = Path(payload.workflow_file)
    env_path = Path(payload.env_file) if payload.env_file else None
    return SimulationParameters(
        workflow_file=workflow_path,
        job=payload.job,
        dry_run=payload.dry_run,
        env_file=env_path,
        env_vars=payload.env_vars,
        verbose=payload.verbose,
    )


def _build_response(result: SimulationResult) -> SimulateResponse:
    """Transform SimulationResult into an API response model."""

    return SimulateResponse(
        success=result.success,
        return_code=result.return_code,
        engine=result.engine,
        stdout=result.stdout,
        stderr=result.stderr,
        metadata=result.metadata,
    )


def create_app() -> FastAPI:
    """Instantiate the FastAPI application."""

    app = FastAPI(title="Actions Simulation Service", version="0.1.0")

    @app.get("/actions/healthz", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/actions/simulate",
        response_model=SimulateResponse,
        tags=["simulation"],
    )
    async def simulate(
        payload: SimulateRequest,
        service: Annotated[SimulationService, Depends(get_simulation_service)],
    ) -> SimulateResponse:
        logger = ActionsLogger(verbose=payload.verbose)
        params = _build_parameters(payload)

        if not params.workflow_file.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"workflow file not found: {params.workflow_file}",
            )

        try:
            result = service.run_simulation(
                params,
                logger=logger,
                capture_output=True,
            )
        except SimulationServiceError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"unexpected error: {exc}",
            ) from exc

        return _build_response(result)

    return app


app = create_app()
