#!/usr/bin/env python3
"""GitHub Actions Simulator - Click/Rich ベース CLI"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import click
from rich.console import Console

from .logger import ActionsLogger
from .simulator import WorkflowSimulator
from .workflow_parser import WorkflowParseError, WorkflowParser


console = Console()


class CLIContext:
    """CLI 全体で共有するコンテキスト情報。"""

    def __init__(self) -> None:
        self.logger: Optional[ActionsLogger] = None


def _build_context(ctx: click.Context, verbose: bool = False) -> CLIContext:
    """コンテキストにロガーを設定して返す。"""

    if ctx.obj is None:
        ctx.obj = CLIContext()

    if ctx.obj.logger is None:
        ctx.obj.logger = ActionsLogger(verbose=verbose)

    return ctx.obj


def run_simulate(
    workflow_file: Path,
    job: Optional[str],
    env_file: Optional[Path],
    dry_run: bool,
    logger: ActionsLogger,
) -> int:
    """ワークフロー実行コマンドの処理"""

    if not workflow_file.exists():
        logger.error(f"ワークフローファイルが見つかりません: {workflow_file}")
        return 1

    logger.info(f"ワークフローを解析中: {workflow_file}")

    # ワークフロー解析
    parser = WorkflowParser()
    try:
        workflow = parser.parse_file(workflow_file)
    except WorkflowParseError as exc:
        logger.error(f"ワークフロー解析エラー: {exc}")
        return 1

    # シミュレーター初期化
    simulator = WorkflowSimulator(logger=logger)

    # 環境変数ファイル読み込み
    if env_file:
        if env_file.exists():
            simulator.load_env_file(env_file)
        else:
            logger.warning(f"環境変数ファイルが見つかりません: {env_file}")

    # 実行
    if dry_run:
        logger.info("ドライランモード: 実際の実行は行いません")
        return simulator.dry_run(workflow, job_name=job)
    else:
        return simulator.run(workflow, job_name=job)


def run_validate(
    workflow_file: Path,
    strict: bool,
    logger: ActionsLogger,
) -> int:
    """ワークフロー検証コマンドの処理"""

    if not workflow_file.exists():
        logger.error(f"ワークフローファイルが見つかりません: {workflow_file}")
        return 1

    logger.info(f"ワークフロー検証中: {workflow_file}")

    # ワークフロー解析・検証
    parser = WorkflowParser()
    try:
        workflow = parser.parse_file(workflow_file)

        if strict:
            # 厳密な検証
            parser.strict_validate(workflow)

        logger.success("ワークフローの検証が完了しました ✓")
        return 0

    except WorkflowParseError as exc:
        logger.error(f"ワークフロー検証エラー: {exc}")
        return 1


def run_list_jobs(
    workflow_file: Path,
    output_format: str,
    logger: ActionsLogger,
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

    if output_format == 'json':
        # JSON形式で出力
        jobs_info: list[dict[str, Any]] = []
        for job_id, job_data in jobs.items():
            jobs_info.append({
                'job_id': job_id,
                'name': job_data.get('name', job_id),
                'runs_on': job_data.get('runs-on', 'unknown'),
                'steps': len(job_data.get('steps', []))
            })
        console.print_json(data=jobs_info)
    else:
        # テーブル形式で出力
        from rich.table import Table

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
@click.pass_context
def cli(ctx: click.Context) -> None:
    """CLIエントリーポイント"""

    if ctx.obj is None:
        ctx.obj = CLIContext()


@cli.command(short_help="ワークフローを実行")
@click.argument("workflow_file")
@click.option("--job", "job", help="実行する特定のジョブ名")
@click.option("--env-file", "env_file", help="環境変数ファイル(.env)")
@click.option("--dry-run", "dry_run", is_flag=True, help="実際に実行せずにプランを表示")
@click.option("--verbose", "-v", is_flag=True, help="詳細ログを表示")
@click.option(
    "--engine",
    type=click.Choice(["builtin", "act"], case_sensitive=False),
    default="builtin",
    show_default=True,
    help="シミュレーションエンジン",
)
@click.pass_context
def simulate(ctx: click.Context, **params: Any) -> None:
    """ワークフローを実行するサブコマンド"""

    context = _build_context(ctx, verbose=bool(params.get("verbose", False)))
    logger = context.logger
    assert logger is not None  # narrow type for static analyzers

    try:
        workflow_path = Path(str(params.get("workflow_file")))
        job_name = str(params.get("job")) if params.get("job") else None
        env_file_path = (
            Path(str(params.get("env_file")))
            if params.get("env_file")
            else None
        )

        status = run_simulate(
            workflow_file=workflow_path,
            job=job_name,
            env_file=env_file_path,
            dry_run=bool(params.get("dry_run", False)),
            logger=logger,
        )
    except Exception as exc:  # pragma: no cover - defensive  # noqa: BLE001
        logger.error(f"エラーが発生しました: {exc}")
        if params.get("verbose"):
            import traceback

            traceback.print_exc()
        raise SystemExit(1) from exc

    raise SystemExit(status)


@cli.command(short_help="ワークフローの構文をチェック")
@click.argument("workflow_file")
@click.option("--strict", "strict", is_flag=True, help="厳密な検証を実行")
@click.option("--verbose", "-v", is_flag=True, help="詳細ログを表示")
@click.pass_context
def validate(ctx: click.Context, **params: Any) -> None:
    """ワークフローの構文をチェックするサブコマンド"""

    context = _build_context(ctx, verbose=bool(params.get("verbose", False)))
    logger = context.logger
    assert logger is not None

    workflow_path = Path(str(params.get("workflow_file")))
    strict_mode = bool(params.get("strict", False))

    status = run_validate(
        workflow_file=workflow_path,
        strict=strict_mode,
        logger=logger,
    )
    raise SystemExit(status)


@cli.command(name="list-jobs", short_help="ジョブ一覧を表示")
@click.argument("workflow_file")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="出力形式",
)
@click.option("--verbose", "-v", is_flag=True, help="詳細ログを表示")
@click.pass_context
def list_jobs(ctx: click.Context, **params: Any) -> None:
    """ジョブ一覧を表示するサブコマンド"""

    context = _build_context(ctx, verbose=bool(params.get("verbose", False)))
    logger = context.logger
    assert logger is not None

    workflow_path = Path(str(params.get("workflow_file")))
    output_format = str(params.get("output_format", "table"))

    status = run_list_jobs(
        workflow_file=workflow_path,
        output_format=output_format,
        logger=logger,
    )
    raise SystemExit(status)


def main() -> None:
    """CLIの実行エントリーポイント"""

    cli.main(prog_name="actions")


if __name__ == "__main__":
    main()
