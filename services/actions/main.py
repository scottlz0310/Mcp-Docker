#!/usr/bin/env python3
"""GitHub Actions Simulator - Click/Rich ベース CLI"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import click
import tomllib
from rich.console import Console
from rich.rule import Rule
from rich.table import Table

from . import __version__ as simulator_version
from .logger import ActionsLogger
from .service import (
    SimulationParameters,
    SimulationResult,
    SimulationService,
    SimulationServiceError,
)
from .workflow_parser import WorkflowParseError, WorkflowParser


class CLIContext:
    """CLI 全体で共有するコンテキスト情報。"""

    def __init__(
        self,
        *,
        verbose: bool = False,
        quiet: bool = False,
        debug: bool = False,
        config_path: Path | None = None,
    ) -> None:
        self.verbose = verbose or debug
        self.quiet = quiet
        self.debug = debug
        self.config_path = config_path
        self.config_data: dict[str, Any] = {}
        self.logger: ActionsLogger | None = None
        self.service: SimulationService | None = None
        self.console: Console = Console(
            quiet=self.quiet,
            highlight=not self.quiet,
        )

    def reconfigure(
        self,
        *,
        verbose: bool | None = None,
        quiet: bool | None = None,
        debug: bool | None = None,
        config_path: Path | None = None,
    ) -> None:
        if verbose is not None:
            self.verbose = verbose or (debug or False)
        if quiet is not None:
            self.quiet = quiet
        if debug is not None:
            self.debug = debug
            if debug:
                self.verbose = True
        if config_path is not None:
            self.config_path = config_path
            self.config_data = {}

        # モード変更時はロガーとコンソールを再初期化する
        self.console = Console(
            quiet=self.quiet,
            highlight=not self.quiet,
        )
        self.logger = None

    def load_config(self) -> None:
        if not self.config_path or self.config_data:
            return

        try:
            with self.config_path.open("rb") as handle:
                self.config_data = tomllib.load(handle)
        except FileNotFoundError:
            self.console.print(
                f"[red]設定ファイルが見つかりません: {self.config_path}[/red]"
            )
        except tomllib.TOMLDecodeError as exc:
            self.console.print(
                f"[red]設定ファイルの読み込みに失敗しました: {exc}[/red]"
            )


def _parse_env_assignments(assignments: Iterable[str]) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for raw in assignments:
        if "=" not in raw:
            raise click.BadParameter(
                f"無効な環境変数形式です: '{raw}'. KEY=VALUE 形式で指定してください。",
                param_hint="--env",
            )
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            raise click.BadParameter(
                f"環境変数名が空です: '{raw}'",
                param_hint="--env",
            )
        env[key] = value
    return env


def _build_context(
    ctx: click.Context,
    *,
    verbose: bool | None = None,
    quiet: bool | None = None,
    debug: bool | None = None,
) -> CLIContext:
    """コンテキストにロガーを設定して返す。"""

    context = ctx.ensure_object(CLIContext)

    if any(value is not None for value in (verbose, quiet, debug)):
        context.reconfigure(
            verbose=context.verbose if verbose is None else verbose,
            quiet=context.quiet if quiet is None else quiet,
            debug=context.debug if debug is None else debug,
        )

    if context.logger is None:
        context.logger = ActionsLogger(
            verbose=context.verbose,
            quiet=context.quiet,
            debug=context.debug,
        )

    if context.service is None:
        context.service = SimulationService()

    return context


def run_simulate(
    workflow_file: Path,
    job: str | None,
    env_file: Path | None,
    dry_run: bool,
    engine: str,
    logger: ActionsLogger,
    console: Console,
    env_vars: Dict[str, str] | None,
    *,
    service: SimulationService,
) -> SimulationResult:
    """ワークフロー実行コマンドの処理"""

    params = SimulationParameters(
        workflow_file=workflow_file,
        engine=engine,
        job=job,
        dry_run=dry_run,
        env_file=env_file,
        verbose=logger.verbose,
        env_vars=env_vars,
    )

    try:
        result = service.run_simulation(
            params,
            logger=logger,
            capture_output=True,
        )
    except SimulationServiceError as exc:
        logger.error(str(exc))
        return SimulationResult(
            success=False,
            return_code=1,
            engine=engine,
            stderr=str(exc),
        )

    if result.stdout:
        console.print(result.stdout.rstrip("\n"))
    if result.stderr:
        console.print(result.stderr.rstrip("\n"), style="red")

    return result


def run_validate(
    workflow_file: Path,
    strict: bool,
    logger: ActionsLogger,
) -> int:
    """ワークフロー検証コマンドの処理"""

    if not workflow_file.exists():
        logger.error(f"ワークフローファイルが見つかりません: {workflow_file}")
        return 1

    targets: List[Path]
    if workflow_file.is_dir():
        yaml_files = set(workflow_file.rglob("*.yml")) | set(
            workflow_file.rglob("*.yaml")
        )
        targets = sorted(yaml_files)
        if not targets:
            logger.warning(
                f"検証対象のワークフローが見つかりません: {workflow_file}"
            )
            return 1
    else:
        targets = [workflow_file]

    overall_success = True
    for target in targets:
        logger.info(f"ワークフロー検証中: {target}")
        parser = WorkflowParser()
        try:
            workflow = parser.parse_file(target)
            if strict:
                parser.strict_validate(workflow)
            logger.success(f"{target} の検証が完了しました ✓")
        except WorkflowParseError as exc:
            overall_success = False
            logger.error(f"{target} の検証エラー: {exc}")

    return 0 if overall_success else 1


def run_list_jobs(
    workflow_file: Path,
    output_format: str,
    logger: ActionsLogger,
    console: Console,
) -> int:
    """ジョブ一覧表示コマンドの処理"""

    if not workflow_file.exists():
        logger.error(f"ワークフローファイルが見つかりません: {workflow_file}")
        return 1

    # ワークフロー解析
    parser = WorkflowParser()
    try:
        workflow = parser.parse_file(workflow_file)
    except WorkflowParseError as exc:
        logger.error(f"ワークフロー解析エラー: {exc}")
        return 1

    jobs = workflow.get('jobs', {})

    if output_format.lower() == 'json':
        jobs_info: list[dict[str, Any]] = []
        for job_id, job_data in jobs.items():
            jobs_info.append({
                'job_id': job_id,
                'name': job_data.get('name', job_id),
                'runs_on': job_data.get('runs-on', 'unknown'),
                'steps': len(job_data.get('steps', [])),
            })
        console.print_json(data=jobs_info)
    else:
        table = Table(title="ジョブ一覧", show_lines=True)
        table.add_column("Job ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Runs on", style="magenta")
        table.add_column("Steps", style="yellow")

        for job_id, job_data in jobs.items():
            job_name = job_data.get('name', job_id)
            runs_on = job_data.get('runs-on', 'unknown')
            steps_count = len(job_data.get('steps', []))
            table.add_row(job_id, job_name, runs_on, str(steps_count))

        console.print(table)

    return 0


@click.group(
    cls=click.Group,
    context_settings={
        "help_option_names": ["-h", "--help"],
        "max_content_width": 100,
    },
    help="""GitHub Actions Simulator

GitHub Actions ワークフローをローカルでシミュレート/検証するためのCLIツールです。

利用可能なサブコマンド:
  - simulate   ワークフローを実行する
  - validate   ワークフローの構文をチェックする
  - list-jobs  ジョブ一覧を表示する
""",
)
@click.option("-v", "--verbose", is_flag=True, help="詳細ログを表示")
@click.option("-q", "--quiet", is_flag=True, help="最小限の出力に切り替える")
@click.option("--debug", is_flag=True, help="デバッグレベルのログを表示")
@click.option(
    "--config",
    type=click.Path(dir_okay=False, path_type=Path),
    help="設定ファイル (TOML) を指定",
)
@click.version_option(  # pragma: no mutate - CLI 表示のみ
    version=simulator_version,
    prog_name="GitHub Actions Simulator",
)
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: bool,
    quiet: bool,
    debug: bool,
    config: Path | None,
) -> None:
    """CLIエントリーポイント"""

    context = ctx.obj if isinstance(ctx.obj, CLIContext) else None
    if context is None:
        context = CLIContext(
            verbose=verbose,
            quiet=quiet,
            debug=debug,
            config_path=config,
        )
    else:
        context.reconfigure(
            verbose=verbose,
            quiet=quiet,
            debug=debug,
            config_path=config,
        )

    ctx.obj = context
    context.load_config()


@cli.command(short_help="ワークフローを実行")
@click.argument(
    "workflow_files",
    nargs=-1,
    type=click.Path(path_type=Path),
)
@click.option("--job", help="実行する特定のジョブ名")
@click.option(
    "--env-file",
    type=click.Path(dir_okay=False, path_type=Path),
    help="環境変数ファイル(.env)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="実際に実行せずにプランを表示",
)
@click.option(
    "--verbose",
    "simulate_verbose",
    is_flag=True,
    help="詳細ログを有効化",
)
@click.option(
    "--quiet",
    "simulate_quiet",
    is_flag=True,
    help="標準出力を抑制",
)
@click.option(
    "--debug",
    "simulate_debug",
    is_flag=True,
    help="デバッグログを有効化 (verboseを暗黙的に有効化)",
)
@click.option(
    "--engine",
    type=click.Choice(["builtin", "act"], case_sensitive=False),
    default="builtin",
    show_default=True,
    help="シミュレーションエンジン",
)
@click.option("--event", "event_name", help="GitHubイベント名を指定")
@click.option("--ref", "git_ref", help="Gitリファレンスを指定")
@click.option("--actor", help="実行ユーザー名を指定")
@click.option(
    "--env",
    "inline_env",
    multiple=True,
    help="追加の環境変数を KEY=VALUE 形式で指定 (複数指定可)",
)
@click.option(
    "--fail-fast",
    is_flag=True,
    help="最初の失敗で残りのワークフローをスキップ",
)
@click.option(
    "--output-format",
    type=click.Choice(["console", "json"], case_sensitive=False),
    default="console",
    show_default=True,
    help="実行サマリーの出力形式",
)
@click.option(
    "--output-file",
    type=click.Path(dir_okay=False, path_type=Path),
    help="サマリーを保存するファイルパス",
)
@click.pass_context
def simulate(
    ctx: click.Context,
    workflow_files: tuple[Path, ...],
    job: str | None,
    env_file: Path | None,
    dry_run: bool,
    simulate_verbose: bool,
    simulate_quiet: bool,
    simulate_debug: bool,
    engine: str,
    event_name: str | None,
    git_ref: str | None,
    actor: str | None,
    inline_env: tuple[str, ...],
    fail_fast: bool,
    output_format: str,
    output_file: Path | None,
) -> None:
    """ワークフローを実行するサブコマンド"""

    context = _build_context(
        ctx,
        verbose=True if simulate_verbose else None,
        quiet=True if simulate_quiet else None,
        debug=True if simulate_debug else None,
    )
    logger = context.logger
    assert logger is not None
    console = context.console

    workflow_paths = list(workflow_files)
    if not workflow_paths:
        console.print("[red]ワークフローファイルを少なくとも1つ指定してください。[/red]")
        raise SystemExit(1)

    env_overrides: Dict[str, str] = {}

    config_env = context.config_data.get("environment")
    if isinstance(config_env, dict):
        for key, value in config_env.items():
            env_overrides[str(key)] = str(value)

    simulator_config = context.config_data.get("simulator", {})
    if isinstance(simulator_config, dict):
        default_event = simulator_config.get("default_event")
        if default_event and not event_name:
            env_overrides.setdefault("GITHUB_EVENT_NAME", str(default_event))
        default_ref = simulator_config.get("default_ref")
        if default_ref and not git_ref:
            env_overrides.setdefault("GITHUB_REF", str(default_ref))
        default_actor = simulator_config.get("default_actor")
        if default_actor and not actor:
            env_overrides.setdefault("GITHUB_ACTOR", str(default_actor))

    if event_name:
        env_overrides["GITHUB_EVENT_NAME"] = event_name
    if git_ref:
        env_overrides["GITHUB_REF"] = git_ref
    if actor:
        env_overrides["GITHUB_ACTOR"] = actor

    if inline_env:
        env_overrides.update(_parse_env_assignments(inline_env))

    env_vars = env_overrides or None
    env_file_path = env_file
    engine_name = engine.lower()

    service = context.service or SimulationService()
    context.service = service

    results: List[tuple[Path, SimulationResult]] = []
    for workflow_path in workflow_paths:
        result = run_simulate(
            workflow_file=workflow_path,
            job=job,
            env_file=env_file_path,
            dry_run=dry_run,
            engine=engine_name,
            logger=logger,
            console=console,
            env_vars=env_vars,
            service=service,
        )
        results.append((workflow_path, result))
        if fail_fast and result.return_code != 0:
            break

    skipped: List[Path] = []
    if len(results) < len(workflow_paths):
        skipped = workflow_paths[len(results):]

    summary_rows: List[Dict[str, object]] = [
        {
            "workflow": str(path),
            "engine": res.engine,
            "status": "success" if res.success else "failed",
            "return_code": res.return_code,
        }
        for path, res in results
    ]
    summary_rows.extend(
        {
            "workflow": str(path),
            "engine": engine_name,
            "status": "skipped",
            "return_code": None,
        }
        for path in skipped
    )

    successful = all(
        row["status"] == "success"
        for row in summary_rows
        if row["status"] != "skipped"
    )
    summary_payload = {
        "results": summary_rows,
        "success": successful,
        "fail_fast_triggered": bool(skipped),
    }

    if output_format.lower() == "json":
        if output_file:
            output_file.write_text(
                json.dumps(summary_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        console.print_json(data=summary_payload)
    else:
        if not context.quiet:
            console.print(Rule("Simulation Summary"))
            table = Table(show_lines=True)
            table.add_column("Workflow", style="cyan")
            table.add_column("Engine", style="magenta")
            table.add_column("Status", style="green")
            table.add_column("Exit Code", style="yellow")
            for row in summary_rows:
                status = str(row["status"])
                status_style = {
                    "success": "green",
                    "failed": "red",
                    "skipped": "yellow",
                }.get(status, "white")
                return_code = row.get("return_code")
                table.add_row(
                    str(row["workflow"]),
                    str(row.get("engine", "")),
                    f"[{status_style}]{status}[/]",
                    "" if return_code is None else str(return_code),
                )
            console.print(table)
            if skipped:
                console.print(
                    "[yellow]fail-fast により {count} 件のワークフローがスキップ"
                    "されました。[/yellow]".format(count=len(skipped))
                )
        if output_file:
            output_file.write_text(
                json.dumps(summary_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    exit_code = 0 if successful else 1
    raise SystemExit(exit_code)


@cli.command(short_help="ワークフローの構文をチェック")
@click.argument("workflow_file", type=click.Path(path_type=Path))
@click.option("--strict", is_flag=True, help="厳密な検証を実行")
@click.pass_context
def validate(
    ctx: click.Context,
    workflow_file: Path,
    strict: bool,
) -> None:
    """ワークフローの構文をチェックするサブコマンド"""

    context = _build_context(ctx)
    logger = context.logger
    assert logger is not None

    status = run_validate(
        workflow_file=workflow_file,
        strict=strict,
        logger=logger,
    )
    raise SystemExit(status)


@cli.command(name="list-jobs", short_help="ジョブ一覧を表示")
@click.argument("workflow_file", type=click.Path(path_type=Path))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="出力形式",
)
@click.pass_context
def list_jobs(
    ctx: click.Context,
    workflow_file: Path,
    output_format: str,
) -> None:
    """ジョブ一覧を表示するサブコマンド"""

    context = _build_context(ctx)
    logger = context.logger
    assert logger is not None

    status = run_list_jobs(
        workflow_file=workflow_file,
        output_format=output_format,
        logger=logger,
        console=context.console,
    )
    raise SystemExit(status)


def main() -> None:
    """CLIの実行エントリーポイント"""

    cli.main(prog_name="actions")


if __name__ == "__main__":
    main()
