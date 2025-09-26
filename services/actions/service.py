"""High-level simulation service shared by CLI and API layers."""

from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Callable

from .act_wrapper import ActWrapper
from .logger import ActionsLogger
from .simulator import SimulationError, WorkflowSimulator
from .workflow_parser import WorkflowParseError, WorkflowParser


@dataclass(slots=True)
class SimulationParameters:
    """Parameters that control a single simulation run."""

    workflow_file: Path
    engine: str = "builtin"
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
    engine: str
    stdout: str = ""
    stderr: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


class SimulationServiceError(Exception):
    """Raised when the simulation service fails to execute a request."""


class SimulationService:
    """Execute workflow simulations using either the builtin engine or act."""

    def __init__(
        self,
        logger_factory: Callable[[bool], ActionsLogger] | None = None,
    ) -> None:
        self._logger_factory: Callable[[bool], ActionsLogger] = (
            logger_factory or self._default_logger_factory
        )

    @staticmethod
    def _default_logger_factory(verbose: bool) -> ActionsLogger:
        return ActionsLogger(verbose=verbose)

    def run_simulation(
        self,
        params: SimulationParameters,
        *,
        logger: ActionsLogger | None = None,
        capture_output: bool = False,
    ) -> SimulationResult:
        """Run the workflow simulation and return a structured result."""

        engine_name = params.engine.lower()
        runner_logger = logger or self._logger_factory(params.verbose)

        stdout_io: StringIO | None = None
        stderr_io: StringIO | None = None
        with ExitStack() as stack:
            if capture_output:
                stdout_io = StringIO()
                stderr_io = StringIO()
                stack.enter_context(redirect_stdout(stdout_io))
                stack.enter_context(redirect_stderr(stderr_io))

            try:
                if engine_name == "act":
                    result = self._run_with_act(params, runner_logger)
                elif engine_name == "builtin":
                    result = self._run_with_builtin(params, runner_logger)
                else:
                    raise SimulationServiceError(
                        f"Unsupported engine: {params.engine}"
                    )
            except SimulationServiceError:
                raise
            except (WorkflowParseError, SimulationError) as exc:
                raise SimulationServiceError(str(exc)) from exc
            except Exception as exc:  # noqa: BLE001 - defensive
                raise SimulationServiceError(
                    f"Unexpected error: {exc}"
                ) from exc

        if capture_output:
            extra_stdout = stdout_io.getvalue() if stdout_io else ""
            extra_stderr = stderr_io.getvalue() if stderr_io else ""
            if extra_stdout:
                result.stdout = f"{extra_stdout}{result.stdout}"
            if extra_stderr:
                result.stderr = f"{extra_stderr}{result.stderr}"

        return result

    def _run_with_builtin(
        self,
        params: SimulationParameters,
        logger: ActionsLogger,
    ) -> SimulationResult:
        if not params.workflow_file.exists():
            raise SimulationServiceError(
                f"ワークフローファイルが見つかりません: {params.workflow_file}"
            )

        logger.info(f"ワークフローを解析中: {params.workflow_file}")

        parser = WorkflowParser()
        workflow = parser.parse_file(params.workflow_file)

        simulator = WorkflowSimulator(logger=logger)

        if params.env_file:
            if params.env_file.exists():
                simulator.load_env_file(params.env_file)
            else:
                logger.warning(f"環境変数ファイルが見つかりません: {params.env_file}")

        if params.env_vars:
            simulator.env_vars.update(params.env_vars)

        if params.dry_run:
            logger.info("ドライランモード: 実際の実行は行いません")
            return_code = simulator.dry_run(workflow, job_name=params.job)
        else:
            return_code = simulator.run(workflow, job_name=params.job)

        success = return_code == 0
        if success:
            logger.success("ワークフローの実行が完了しました ✓")
        else:
            logger.error("ワークフローの実行に失敗しました")

        return SimulationResult(
            success=success,
            return_code=return_code,
            engine="builtin",
        )

    def _run_with_act(
        self,
        params: SimulationParameters,
        logger: ActionsLogger,
    ) -> SimulationResult:
        if not params.workflow_file.exists():
            raise SimulationServiceError(
                f"ワークフローファイルが見つかりません: {params.workflow_file}"
            )

        env_vars: dict[str, str] | None = None
        if params.env_file:
            if params.env_file.exists():
                env_vars = _load_env_file_as_dict(params.env_file, logger)
            else:
                logger.warning(f"環境変数ファイルが見つかりません: {params.env_file}")

        if params.env_vars:
            env_vars = {**(env_vars or {}), **params.env_vars}

        try:
            wrapper = ActWrapper(
                working_directory=str(params.workflow_file.parent)
            )
        except RuntimeError as exc:
            raise SimulationServiceError(str(exc)) from exc

        result = wrapper.run_workflow(
            workflow_file=str(params.workflow_file),
            job=params.job,
            dry_run=params.dry_run,
            verbose=params.verbose,
            env_vars=env_vars,
        )

        success = bool(result.get("success"))
        return_code = int(result.get("returncode", 1))
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")

        if success:
            logger.success("act でのワークフロー実行が完了しました ✓")
        else:
            logger.error(f"act 実行が失敗しました (returncode={return_code})")

        return SimulationResult(
            success=success,
            return_code=return_code,
            engine="act",
            stdout=stdout,
            stderr=stderr,
            metadata={"command": result.get("command")},
        )


def _load_env_file_as_dict(
    env_file: Path,
    logger: ActionsLogger,
) -> dict[str, str]:
    env_vars: dict[str, str] = {}
    try:
        with env_file.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    logger.warning(
                        f"環境変数ファイルの形式が無効です (無視します): {line}"
                    )
                    continue
                key, value = line.split("=", 1)
                env_vars[key] = value
    except OSError as exc:
        logger.error(f"環境変数ファイルの読み込みに失敗しました: {exc}")

    return env_vars
