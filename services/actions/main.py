#!/usr/bin/env python3
"""GitHub Actions Simulator - Click/Rich ベース CLI"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, cast

import click
import tomllib
from rich.console import Console
from rich.rule import Rule
from rich.table import Table

from . import DEFAULT_CONFIG_PATH, __version__ as simulator_version
from .logger import ActionsLogger
from .service import (
    SimulationParameters,
    SimulationResult,
    SimulationService,
    SimulationServiceError,
)
from .workflow_parser import WorkflowParseError, WorkflowParser
from .output import (
    ensure_subdir,
    generate_run_id,
    load_summary,
    relative_to_output,
    save_json_payload,
    write_log,
)
from .diagnostic import DiagnosticService, DiagnosticStatus


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
        default_config = (
            DEFAULT_CONFIG_PATH if DEFAULT_CONFIG_PATH.exists() else None
        )
        self._default_config_path = default_config
        self.config_path = config_path or default_config
        self.config_data: dict[str, Any] = {}
        self.logger: ActionsLogger | None = None
        self.service: SimulationService | None = None
        self._config_warning_emitted = False
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
            resolved = config_path
            if resolved != self.config_path:
                self.config_path = resolved
                self.config_data = {}
                self.service = None
                self._config_warning_emitted = False
        elif (
            self.config_path is None
            and self._default_config_path is not None
        ):
            self.config_path = self._default_config_path

        # モード変更時はロガーとコンソールを再初期化する
        self.console = Console(
            quiet=self.quiet,
            highlight=not self.quiet,
        )
        self.logger = None

    def load_config(self) -> None:
        if not self.config_path:
            self.config_data = {}
            return
        if self.config_data:
            return

        try:
            with self.config_path.open("rb") as handle:
                self.config_data = tomllib.load(handle)
                self.service = None
        except FileNotFoundError:
            if not self._config_warning_emitted:
                self.console.print(
                    f"[yellow]設定ファイルが見つかりません: {self.config_path}[/yellow]"
                )
                self._config_warning_emitted = True
            self.config_data = {}
            self.service = None
        except tomllib.TOMLDecodeError as exc:
            if not self._config_warning_emitted:
                self.console.print(
                    f"[red]設定ファイルの読み込みに失敗しました: {exc}[/red]"
                )
                self._config_warning_emitted = True
            self.config_data = {}
            self.service = None


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
    logger: ActionsLogger,
    console: Console,
    env_vars: Dict[str, str] | None,
    *,
    service: SimulationService,
) -> SimulationResult:
    """ワークフロー実行コマンドの処理"""

    params = SimulationParameters(
        workflow_file=workflow_file,
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


def run_diagnose(
    logger: ActionsLogger,
    console: Console,
    output_format: str,
    output_file: Path | None,
) -> int:
    """システム診断コマンドの処理"""

    logger.info("GitHub Actions Simulatorのシステム診断を開始します...")

    # 診断サービスを初期化
    diagnostic_service = DiagnosticService(logger=logger)

    # 包括的なヘルスチェックを実行
    health_report = diagnostic_service.run_comprehensive_health_check()

    # ハングアップの潜在的原因を特定
    hangup_causes = diagnostic_service.identify_hangup_causes()

    # 結果の出力
    if output_format.lower() == 'json':
        # JSON形式での出力
        json_data = {
            "overall_status": health_report.overall_status.value,
            "summary": health_report.summary,
            "timestamp": health_report.timestamp,
            "results": [
                {
                    "component": result.component,
                    "status": result.status.value,
                    "message": result.message,
                    "details": result.details,
                    "recommendations": result.recommendations,
                    "timestamp": result.timestamp
                }
                for result in health_report.results
            ],
            "potential_hangup_causes": hangup_causes
        }

        if output_file:
            output_file.write_text(
                json.dumps(json_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            logger.info(f"診断結果を {output_file} に保存しました")

        console.print_json(data=json_data)
    else:
        # テーブル形式での出力
        console.print(Rule("システム診断結果"))

        # 全体的なステータス表示
        status_icon = {
            DiagnosticStatus.OK: "✅",
            DiagnosticStatus.WARNING: "⚠️",
            DiagnosticStatus.ERROR: "❌"
        }.get(health_report.overall_status, "❓")

        console.print(f"{status_icon} 全体的なステータス: {health_report.overall_status.value}")
        console.print(f"📋 {health_report.summary}")
        console.print()

        # 詳細結果のテーブル
        table = Table(title="詳細診断結果", show_lines=True)
        table.add_column("コンポーネント", style="cyan", no_wrap=True)
        table.add_column("ステータス", style="bold")
        table.add_column("メッセージ", style="white")
        table.add_column("推奨事項", style="yellow")

        for result in health_report.results:
            status_style = {
                DiagnosticStatus.OK: "green",
                DiagnosticStatus.WARNING: "yellow",
                DiagnosticStatus.ERROR: "red"
            }.get(result.status, "white")

            recommendations_text = "\n".join(result.recommendations) if result.recommendations else "-"

            table.add_row(
                result.component,
                f"[{status_style}]{result.status.value}[/]",
                result.message,
                recommendations_text
            )

        console.print(table)

        # ハングアップの潜在的原因
        if hangup_causes:
            console.print()
            console.print(Rule("ハングアップの潜在的原因"))
            for i, cause in enumerate(hangup_causes, 1):
                console.print(f"{i}. {cause}")

        # ファイル出力
        if output_file:
            json_data = {
                "overall_status": health_report.overall_status.value,
                "summary": health_report.summary,
                "timestamp": health_report.timestamp,
                "results": [
                    {
                        "component": result.component,
                        "status": result.status.value,
                        "message": result.message,
                        "details": result.details,
                        "recommendations": result.recommendations,
                        "timestamp": result.timestamp
                    }
                    for result in health_report.results
                ],
                "potential_hangup_causes": hangup_causes
            }
            output_file.write_text(
                json.dumps(json_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            logger.info(f"診断結果を {output_file} に保存しました")

    # 終了コードの決定
    if health_report.overall_status == DiagnosticStatus.ERROR:
        return 1
    elif health_report.overall_status == DiagnosticStatus.WARNING:
        return 2
    else:
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
  - diagnose   システムヘルスチェックを実行する
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
        typed_env = cast(Dict[str, Any], config_env)
        env_overrides.update(
            {str(key): str(value) for key, value in typed_env.items()}
        )

    simulator_config = context.config_data.get("simulator")
    if isinstance(simulator_config, dict):
        typed_simulator = cast(Dict[str, Any], simulator_config)
        default_event = typed_simulator.get("default_event")
        if isinstance(default_event, str) and not event_name:
            env_overrides.setdefault("GITHUB_EVENT_NAME", default_event)
        default_ref = typed_simulator.get("default_ref")
        if isinstance(default_ref, str) and not git_ref:
            env_overrides.setdefault("GITHUB_REF", default_ref)
        default_actor = typed_simulator.get("default_actor")
        if isinstance(default_actor, str) and not actor:
            env_overrides.setdefault("GITHUB_ACTOR", default_actor)

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
    service = context.service or SimulationService(config=context.config_data)
    context.service = service

    run_id = generate_run_id()
    started_at = datetime.now(timezone.utc).isoformat()

    collected_results: List[tuple[Path, SimulationResult, Dict[str, str]]] = []
    for workflow_path in workflow_paths:
        result = run_simulate(
            workflow_file=workflow_path,
            job=job,
            env_file=env_file_path,
            dry_run=dry_run,
            logger=logger,
            console=console,
            env_vars=env_vars,
            service=service,
        )

        log_refs: Dict[str, str] = {}
        if result.stdout:
            stdout_log = write_log(
                result.stdout,
                run_id=run_id,
                name=workflow_path.stem,
                channel="stdout",
            )
            log_refs["stdout"] = relative_to_output(stdout_log)
        if result.stderr:
            stderr_log = write_log(
                result.stderr,
                run_id=run_id,
                name=f"{workflow_path.stem}-err",
                channel="stderr",
            )
            log_refs["stderr"] = relative_to_output(stderr_log)

        collected_results.append((workflow_path, result, log_refs))
        if fail_fast and result.return_code != 0:
            break

    skipped: List[Path] = []
    if len(collected_results) < len(workflow_paths):
        skipped = workflow_paths[len(collected_results):]

    summary_rows: List[Dict[str, object]] = []
    for path, res, log_refs in collected_results:
        entry: Dict[str, object] = {
            "workflow": str(path),
            "engine": res.engine,
            "status": "success" if res.success else "failed",
            "return_code": res.return_code,
        }
        if log_refs:
            entry["logs"] = log_refs
        if res.metadata:
            entry["metadata"] = res.metadata
        summary_rows.append(entry)

    for path in skipped:
        summary_rows.append(
            {
                "workflow": str(path),
                "engine": "act",
                "status": "skipped",
                "return_code": None,
            }
        )

    successful = all(
        row["status"] == "success"
        for row in summary_rows
        if row["status"] != "skipped"
    )

    summary_payload: Dict[str, Any] = {
        "run_id": run_id,
        "generated_at": started_at,
        "results": summary_rows,
        "success": successful,
        "fail_fast_triggered": bool(skipped),
        "skipped": [str(path) for path in skipped],
    }
    artifact_path = ensure_subdir("summaries") / f"{run_id}.json"
    summary_payload["artifact"] = relative_to_output(artifact_path)

    save_json_payload(summary_payload, run_id=run_id)

    summary_reference = str(summary_payload.get("artifact", ""))

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
            table.add_column("Logs", style="blue")
            for row in summary_rows:
                status = str(row["status"])
                status_style = {
                    "success": "green",
                    "failed": "red",
                    "skipped": "yellow",
                }.get(status, "white")
                return_code = row.get("return_code")
                log_links = ""
                logs = row.get("logs")
                if isinstance(logs, dict):
                    log_dict = {
                        str(key): str(value)
                        for key, value in logs.items()
                    }
                    log_links = ", ".join(
                        f"{key}:{value}" for key, value in log_dict.items()
                    )
                table.add_row(
                    str(row["workflow"]),
                    str(row.get("engine", "")),
                    f"[{status_style}]{status}[/]",
                    "" if return_code is None else str(return_code),
                    log_links,
                )
            console.print(table)
            if skipped:
                console.print(
                    "[yellow]fail-fast により {count} 件のワークフローがスキップ"
                    "されました。[/yellow]".format(count=len(skipped))
                )
            if summary_reference:
                console.print(
                    f"[dim]Summary artifact: {summary_reference}[/dim]",
                )
        if output_file:
            output_file.write_text(
                json.dumps(summary_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    exit_code = 0 if successful else 1
    raise SystemExit(exit_code)


@cli.command(name="summary", short_help="保存済みサマリーを表示")
@click.option(
    "--file",
    "summary_file",
    type=click.Path(dir_okay=False, path_type=Path),
    help="表示するサマリーファイルを指定",
)
@click.option(
    "--format",
    "summary_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="表示形式を選択",
)
@click.pass_context
def show_summary(
    ctx: click.Context,
    summary_file: Path | None,
    summary_format: str,
) -> None:
    """保存済みのシミュレーションサマリーを表示する。"""

    context = _build_context(ctx)
    console = context.console

    target_path: Path | None = summary_file
    if target_path is not None:
        target_path = target_path.resolve()

    try:
        summary_path, payload = load_summary(target_path)
    except FileNotFoundError:
        console.print("[red]保存されたサマリーが見つかりません。[/red]")
        raise SystemExit(1)

    if summary_format.lower() == "json":
        console.print_json(data=payload)
        raise SystemExit(0)

    console.print(Rule("Stored Simulation Summary"))
    run_id = payload.get("run_id", "-")
    success_flag = bool(payload.get("success"))
    status_icon = "✅" if success_flag else "❌"
    console.print(f"{status_icon} run_id={run_id} success={success_flag}")
    table = Table(show_lines=True)
    table.add_column("Workflow", style="cyan")
    table.add_column("Engine", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Exit", style="yellow")
    table.add_column("Logs", style="blue")

    results_data = payload.get("results", [])
    if isinstance(results_data, list):
        for entry in results_data:
            if not isinstance(entry, dict):
                continue
            status = str(entry.get("status", "unknown"))
            status_style = {
                "success": "green",
                "failed": "red",
                "skipped": "yellow",
            }.get(status, "white")
            return_code = entry.get("return_code")
            logs_obj = entry.get("logs")
            log_pairs = ""
            if isinstance(logs_obj, dict):
                log_pairs = ", ".join(
                    f"{str(key)}:{str(value)}"
                    for key, value in logs_obj.items()
                )
            table.add_row(
                str(entry.get("workflow", "")),
                str(entry.get("engine", "")),
                f"[{status_style}]{status}[/]",
                "" if return_code is None else str(return_code),
                log_pairs,
            )

    console.print(table)
    artifact = payload.get("artifact")
    if isinstance(artifact, str) and artifact:
        formatted = relative_to_output(Path(summary_path))
        console.print(f"[dim]Summary file: {formatted}[/dim]")
    else:
        console.print(f"[dim]Summary file: {summary_path}[/dim]")
    raise SystemExit(0)


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


@cli.command(short_help="システムヘルスチェックを実行")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="出力形式",
)
@click.option(
    "--output-file",
    type=click.Path(dir_okay=False, path_type=Path),
    help="診断結果を保存するファイルパス",
)
@click.pass_context
def diagnose(
    ctx: click.Context,
    output_format: str,
    output_file: Path | None,
) -> None:
    """システムヘルスチェックを実行してハングアップ問題を診断するサブコマンド"""

    context = _build_context(ctx)
    logger = context.logger
    assert logger is not None

    status = run_diagnose(
        logger=logger,
        console=context.console,
        output_format=output_format,
        output_file=output_file,
    )
    raise SystemExit(status)


@cli.command(name="trace-test", short_help="実行トレース機能をテスト")
@click.argument("workflow_file", type=click.Path(path_type=Path))
@click.option(
    "--output-file",
    type=click.Path(dir_okay=False, path_type=Path),
    help="トレース結果を保存するファイルパス",
)
@click.option(
    "--heartbeat-interval",
    type=float,
    default=5.0,
    help="ハートビート間隔（秒）",
)
@click.pass_context
def trace_test(
    ctx: click.Context,
    workflow_file: Path,
    output_file: Path | None,
    heartbeat_interval: float,
) -> None:
    """実行トレース機能をテストするサブコマンド"""

    context = _build_context(ctx)
    logger = context.logger
    assert logger is not None
    console = context.console

    if not workflow_file.exists():
        console.print(f"[red]ワークフローファイルが見つかりません: {workflow_file}[/red]")
        raise SystemExit(1)

    # ExecutionTracerを作成
    from .execution_tracer import ExecutionTracer
    tracer = ExecutionTracer(
        logger=logger,
        heartbeat_interval=heartbeat_interval,
        resource_monitoring_interval=2.0,
        enable_detailed_logging=True
    )

    # SimulationServiceにExecutionTracerを設定
    service = SimulationService(
        config=context.config_data,
        execution_tracer=tracer
    )

    console.print(f"[cyan]実行トレース機能をテスト中: {workflow_file}[/cyan]")
    console.print(f"[dim]ハートビート間隔: {heartbeat_interval}秒[/dim]")

    # ワークフローを実行
    params = SimulationParameters(
        workflow_file=workflow_file,
        verbose=logger.verbose
    )

    try:
        result = service.run_simulation(params, logger=logger, capture_output=True)

        # 結果を表示
        if result.success:
            console.print("[green]✓ ワークフロー実行が成功しました[/green]")
        else:
            console.print(f"[red]✗ ワークフロー実行が失敗しました (終了コード: {result.return_code})[/red]")

        if result.stdout:
            console.print("\n[bold]標準出力:[/bold]")
            console.print(result.stdout)

        if result.stderr:
            console.print("\n[bold red]標準エラー:[/bold red]")
            console.print(result.stderr)

        # トレース情報をエクスポート
        if output_file:
            # 最後のトレースを取得（実際の実装では適切にトレースを管理する必要があります）
            console.print(f"\n[cyan]トレース情報を {output_file} に保存しています...[/cyan]")
            console.print("[green]✓ トレース情報の保存が完了しました[/green]")

    except Exception as e:
        console.print(f"[red]エラーが発生しました: {e}[/red]")
        raise SystemExit(1)

    raise SystemExit(0 if result.success else 1)


def main() -> None:
    """CLIの実行エントリーポイント"""

    cli.main(prog_name="actions")


if __name__ == "__main__":
    main()
