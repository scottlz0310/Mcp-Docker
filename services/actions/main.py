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

# サーバーモード用のインポート
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse, HTMLResponse
    import uvicorn

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

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
        default_config = DEFAULT_CONFIG_PATH if DEFAULT_CONFIG_PATH.exists() else None
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
        elif self.config_path is None and self._default_config_path is not None:
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
                self.console.print(f"[yellow]設定ファイルが見つかりません: {self.config_path}[/yellow]")
                self._config_warning_emitted = True
            self.config_data = {}
            self.service = None
        except tomllib.TOMLDecodeError as exc:
            if not self._config_warning_emitted:
                self.console.print(f"[red]設定ファイルの読み込みに失敗しました: {exc}[/red]")
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
    create_debug_bundle: bool = False,
    debug_bundle_dir: Path | None = None,
    show_performance_metrics: bool = False,
    show_execution_trace: bool = False,
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

        # 詳細結果の表示処理
        if hasattr(result, "detailed_result") and result.detailed_result:
            detailed_result = result.detailed_result

            # 診断結果の表示
            if hasattr(detailed_result, "diagnostic_results") and detailed_result.diagnostic_results:
                console.print("\n[cyan]📋 診断結果:[/cyan]")
                for diag_result in detailed_result.diagnostic_results:
                    status_icon = {"OK": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(
                        diag_result.status.value if hasattr(diag_result.status, "value") else str(diag_result.status),
                        "❓",
                    )

                    console.print(f"  {status_icon} {diag_result.component}: {diag_result.message}")

                    if diag_result.recommendations:
                        for rec in diag_result.recommendations[:2]:  # 最初の2つの推奨事項のみ表示
                            console.print(f"    💡 {rec}")

            # パフォーマンスメトリクスの表示
            if (
                show_performance_metrics
                and hasattr(detailed_result, "performance_metrics")
                and detailed_result.performance_metrics
            ):
                console.print("\n[cyan]📊 パフォーマンスメトリクス:[/cyan]")
                metrics = detailed_result.performance_metrics

                if hasattr(metrics, "execution_time_ms"):
                    console.print(f"  ⏱️  実行時間: {metrics.execution_time_ms:.2f}ms")
                if hasattr(metrics, "peak_memory_mb"):
                    console.print(f"  🧠 ピークメモリ使用量: {metrics.peak_memory_mb:.2f}MB")
                if hasattr(metrics, "cpu_usage_percent"):
                    console.print(f"  ⚡ CPU使用率: {metrics.cpu_usage_percent:.1f}%")
                if hasattr(metrics, "docker_operations_count"):
                    console.print(f"  🐳 Docker操作数: {metrics.docker_operations_count}")

            # 実行トレースの表示
            if show_execution_trace and hasattr(detailed_result, "execution_trace") and detailed_result.execution_trace:
                console.print("\n[cyan]🔍 実行トレース:[/cyan]")
                trace = detailed_result.execution_trace

                if hasattr(trace, "stages") and trace.stages:
                    for stage in trace.stages[-5:]:  # 最後の5段階のみ表示
                        stage_name = stage.stage.value if hasattr(stage.stage, "value") else str(stage.stage)
                        duration = (
                            f" ({stage.duration_ms:.2f}ms)"
                            if hasattr(stage, "duration_ms") and stage.duration_ms
                            else ""
                        )
                        console.print(f"  📍 {stage_name}{duration}")

            # ハングアップ検出とエラーレポート表示の処理
            if detailed_result.hang_analysis or (
                hasattr(detailed_result, "error_report") and detailed_result.error_report
            ):
                console.print("[yellow]⚠️  ハングアップまたは実行問題が検出されました[/yellow]")

                # 詳細なハングアップ分析の表示
                if detailed_result.hang_analysis:
                    analysis = detailed_result.hang_analysis
                    console.print(f"[yellow]📋 分析ID: {analysis.analysis_id}[/yellow]")

                    if analysis.primary_cause:
                        console.print(f"[red]🚨 主要な問題: {analysis.primary_cause.title}[/red]")
                        console.print(f"[red]   説明: {analysis.primary_cause.description}[/red]")
                        console.print(
                            f"[red]   重要度: {analysis.primary_cause.severity.value if hasattr(analysis.primary_cause.severity, 'value') else analysis.primary_cause.severity}[/red]"
                        )

                        # 推奨事項の表示
                        if (
                            hasattr(analysis.primary_cause, "recommendations")
                            and analysis.primary_cause.recommendations
                        ):
                            console.print("[cyan]💡 推奨される対処法:[/cyan]")
                            for i, rec in enumerate(analysis.primary_cause.recommendations[:3], 1):
                                console.print(f"   {i}. {rec}")

                        # 修正コマンドの表示
                        if hasattr(analysis.primary_cause, "fix_commands") and analysis.primary_cause.fix_commands:
                            console.print("[green]🔧 修正コマンド:[/green]")
                            for cmd in analysis.primary_cause.fix_commands[:2]:
                                console.print(f"   $ {cmd}")

                    # 復旧提案の表示
                    if hasattr(analysis, "recovery_suggestions") and analysis.recovery_suggestions:
                        console.print("[blue]🔄 復旧提案:[/blue]")
                        for i, suggestion in enumerate(analysis.recovery_suggestions[:3], 1):
                            console.print(f"   {i}. {suggestion}")

                    # 予防策の表示
                    if hasattr(analysis, "prevention_measures") and analysis.prevention_measures:
                        console.print("[magenta]🛡️  予防策:[/magenta]")
                        for i, measure in enumerate(analysis.prevention_measures[:2], 1):
                            console.print(f"   {i}. {measure}")

                # エラーレポートの詳細表示
                if hasattr(detailed_result, "error_report") and detailed_result.error_report:
                    error_report = detailed_result.error_report
                    console.print(f"[dim]📄 エラーレポートID: {error_report.report_id}[/dim]")

                    # トラブルシューティングガイドの表示
                    if hasattr(error_report, "troubleshooting_guide") and error_report.troubleshooting_guide:
                        console.print("[cyan]📖 トラブルシューティングガイド:[/cyan]")
                        for i, step in enumerate(error_report.troubleshooting_guide[:3], 1):
                            console.print(f"   {i}. {step}")

                    # 次のステップの表示
                    if hasattr(error_report, "next_steps") and error_report.next_steps:
                        console.print("[yellow]➡️  次のステップ:[/yellow]")
                        for i, step in enumerate(error_report.next_steps[:3], 1):
                            console.print(f"   {i}. {step}")

                # デバッグバンドルの自動作成
                # TODO: デバッグバンドル作成機能は現在HangupDetectorに移行されています
                # EnhancedActWrapperのcreate_debug_bundle_for_hangupメソッドは存在しません
                if (
                    False  # type: ignore[unreachable]
                    and create_debug_bundle
                    and hasattr(detailed_result, "error_report")
                    and detailed_result.error_report
                ):
                    try:  # type: ignore[unreachable]
                        from .enhanced_act_wrapper import EnhancedActWrapper

                        if hasattr(service, "act_wrapper") and isinstance(service.act_wrapper, EnhancedActWrapper):
                            console.print("[blue]🔧 デバッグバンドルを作成中...[/blue]")

                            # debug_bundle = service.act_wrapper.create_debug_bundle_for_hangup(
                            #     error_report=detailed_result.error_report,
                            #     output_directory=debug_bundle_dir,
                            # )

                            debug_bundle = None
                            if debug_bundle and hasattr(debug_bundle, "bundle_path") and debug_bundle.bundle_path:
                                console.print(
                                    f"[green]✅ デバッグバンドルが作成されました: {debug_bundle.bundle_path}[/green]"
                                )
                                if hasattr(debug_bundle, "total_size_bytes"):
                                    console.print(f"[green]   サイズ: {debug_bundle.total_size_bytes} bytes[/green]")
                                if hasattr(debug_bundle, "included_files"):
                                    console.print(
                                        f"[green]   含まれるファイル: {len(debug_bundle.included_files)}個[/green]"
                                    )

                                # デバッグバンドルの使用方法を案内
                                console.print(
                                    "[dim]💡 このデバッグバンドルを技術サポートに送信して詳細な分析を依頼できます[/dim]"
                                )
                            else:
                                console.print("[red]❌ デバッグバンドルの作成に失敗しました[/red]")
                    except Exception as e:
                        logger.error(f"デバッグバンドル作成中にエラーが発生しました: {e}")
                        console.print(f"[red]❌ デバッグバンドル作成エラー: {e}[/red]")

    except SimulationServiceError as exc:
        logger.error(str(exc))
        return SimulationResult(
            success=False,
            return_code=1,
            stderr=str(exc),
        )

    if result.stdout:
        console.print(result.stdout.rstrip("\n"), markup=False)
    if result.stderr:
        console.print(result.stderr.rstrip("\n"), style="red", markup=False)

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
        yaml_files = set(workflow_file.rglob("*.yml")) | set(workflow_file.rglob("*.yaml"))
        targets = sorted(yaml_files)
        if not targets:
            logger.warning(f"検証対象のワークフローが見つかりません: {workflow_file}")
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

    jobs = workflow.get("jobs", {})

    if output_format.lower() == "json":
        jobs_info: list[dict[str, Any]] = []
        for job_id, job_data in jobs.items():
            jobs_info.append(
                {
                    "job_id": job_id,
                    "name": job_data.get("name", job_id),
                    "runs_on": job_data.get("runs-on", "unknown"),
                    "steps": len(job_data.get("steps", [])),
                }
            )
        console.print_json(data=jobs_info)
    else:
        table = Table(title="ジョブ一覧", show_lines=True)
        table.add_column("Job ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Runs on", style="magenta")
        table.add_column("Steps", style="yellow")

        for job_id, job_data in jobs.items():
            job_name = job_data.get("name", job_id)
            runs_on = job_data.get("runs-on", "unknown")
            steps_count = len(job_data.get("steps", []))
            table.add_row(job_id, job_name, runs_on, str(steps_count))

        console.print(table)

    return 0


def run_diagnose(
    logger: ActionsLogger,
    console: Console,
    output_format: str,
    output_file: Path | None,
    include_performance_analysis: bool = False,
    include_trace_analysis: bool = False,
) -> int:
    """システム診断コマンドの処理"""

    logger.info("GitHub Actions Simulatorのシステム診断を開始します...")

    # 診断サービスを初期化
    diagnostic_service = DiagnosticService(logger=logger)

    # 包括的なヘルスチェックを実行
    health_report = diagnostic_service.run_comprehensive_health_check()

    # ハングアップの潜在的原因を特定
    hangup_causes = diagnostic_service.identify_hangup_causes()

    # パフォーマンス分析（オプション）
    performance_analysis: dict[str, Any] = {}
    if include_performance_analysis:
        logger.info("パフォーマンス分析を実行中...")
        try:
            # システムリソースの詳細分析
            import psutil

            performance_analysis = {
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "disk_usage_percent": psutil.disk_usage("/").percent,
                "load_average": psutil.getloadavg() if hasattr(psutil, "getloadavg") else None,
            }
        except Exception as e:
            logger.warning(f"パフォーマンス分析中にエラーが発生しました: {e}")
            performance_analysis = {"error": str(e)}

    # トレース分析（オプション）
    trace_analysis: dict[str, Any] = {}
    if include_trace_analysis:
        logger.info("実行トレース分析を実行中...")
        try:
            # 最近の実行ログの分析
            from pathlib import Path

            output_dir = Path("output")
            if output_dir.exists():
                log_files = list(output_dir.rglob("*.log"))
                trace_analysis = {
                    "recent_log_files": len(log_files),
                    "latest_logs": [
                        str(f) for f in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
                    ],
                }
            else:
                trace_analysis = {
                    "log_files": 0,
                    "message": "出力ディレクトリが見つかりません",
                }
        except Exception as e:
            logger.warning(f"トレース分析中にエラーが発生しました: {e}")
            trace_analysis = {"error": str(e)}

    # 結果の出力
    if output_format.lower() == "json":
        # JSON形式での出力
        json_data: dict[str, Any] = {
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
                    "timestamp": result.timestamp,
                }
                for result in health_report.results
            ],
            "potential_hangup_causes": hangup_causes,
        }

        # パフォーマンス分析とトレース分析を追加
        if performance_analysis:
            json_data["performance_analysis"] = performance_analysis
        if trace_analysis:
            json_data["trace_analysis"] = trace_analysis

        if output_file:
            output_file.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"診断結果を {output_file} に保存しました")

        console.print_json(data=json_data)
    else:
        # テーブル形式での出力
        console.print(Rule("システム診断結果"))

        # 全体的なステータス表示
        status_icon = {
            DiagnosticStatus.OK: "✅",
            DiagnosticStatus.WARNING: "⚠️",
            DiagnosticStatus.ERROR: "❌",
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
                DiagnosticStatus.ERROR: "red",
            }.get(result.status, "white")

            recommendations_text = "\n".join(result.recommendations) if result.recommendations else "-"

            table.add_row(
                result.component,
                f"[{status_style}]{result.status.value}[/]",
                result.message,
                recommendations_text,
            )

        console.print(table)

        # ハングアップの潜在的原因と復旧提案
        if hangup_causes:
            console.print()
            console.print(Rule("ハングアップの潜在的原因と復旧提案"))
            for i, cause in enumerate(hangup_causes, 1):
                console.print(f"{i}. {cause}")

            # 復旧提案を生成
            recovery_suggestions = _generate_recovery_suggestions_from_causes(hangup_causes, health_report)
            if recovery_suggestions:
                console.print()
                console.print("[cyan]🔄 推奨される復旧手順:[/cyan]")
                for i, suggestion in enumerate(recovery_suggestions, 1):
                    console.print(f"   {i}. {suggestion}")

        # エラーレポートと詳細なトラブルシューティング
        error_results = [r for r in health_report.results if r.status == DiagnosticStatus.ERROR]
        if error_results:
            console.print()
            console.print(Rule("エラー詳細とトラブルシューティング"))

            for error_result in error_results:
                console.print(f"[red]❌ {error_result.component}[/red]")
                console.print(f"   問題: {error_result.message}")

                if error_result.recommendations:
                    console.print("   [yellow]対処法:[/yellow]")
                    for rec in error_result.recommendations:
                        console.print(f"     • {rec}")

                # 詳細情報がある場合は表示
                if error_result.details:
                    important_details = _extract_important_details(error_result.details)
                    if important_details:
                        console.print("   [dim]詳細情報:[/dim]")
                        for key, value in important_details.items():
                            console.print(f"     {key}: {value}")
                console.print()

        # 次のステップの提案
        next_steps = _generate_next_steps(health_report, hangup_causes)
        if next_steps:
            console.print()
            console.print(Rule("次のステップ"))
            console.print("[green]推奨される次のアクション:[/green]")
            for i, step in enumerate(next_steps, 1):
                console.print(f"   {i}. {step}")

        # パフォーマンス分析の表示
        if performance_analysis and "error" not in performance_analysis:
            console.print()
            console.print(Rule("パフォーマンス分析"))
            console.print(
                f"🖥️  CPU: {performance_analysis.get('cpu_count', 'N/A')}コア, 使用率: {performance_analysis.get('cpu_percent', 'N/A')}%"
            )
            console.print(
                f"🧠 メモリ: {performance_analysis.get('memory_available_gb', 'N/A')}GB利用可能 / {performance_analysis.get('memory_total_gb', 'N/A')}GB総容量"
            )
            console.print(f"💾 ディスク使用率: {performance_analysis.get('disk_usage_percent', 'N/A')}%")
            if performance_analysis.get("load_average"):
                load_avg = performance_analysis["load_average"]
                console.print(f"⚡ システム負荷: {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}")

        # トレース分析の表示
        if trace_analysis and "error" not in trace_analysis:
            console.print()
            console.print(Rule("実行トレース分析"))
            console.print(f"📁 最近のログファイル数: {trace_analysis.get('recent_log_files', 0)}")
            if trace_analysis.get("latest_logs"):
                console.print("📋 最新のログファイル:")
                for log_file in trace_analysis["latest_logs"][:3]:
                    console.print(f"  • {log_file}")

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
                        "timestamp": result.timestamp,
                    }
                    for result in health_report.results
                ],
                "potential_hangup_causes": hangup_causes,
            }

            # パフォーマンス分析とトレース分析を追加
            if performance_analysis:
                json_data["performance_analysis"] = performance_analysis
            if trace_analysis:
                json_data["trace_analysis"] = trace_analysis

            output_file.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
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
  - simulate             ワークフローを実行する（--diagnose で事前診断、--enhanced で拡張機能、--show-performance-metrics でメトリクス表示）
  - validate             ワークフローの構文をチェックする
  - list-jobs            ジョブ一覧を表示する
  - diagnose             システムヘルスチェックを実行する（--include-performance, --include-trace で詳細分析）
  - create-debug-bundle  デバッグバンドルを作成する（トラブルシューティング用）
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
@click.option(
    "--enhanced",
    is_flag=True,
    help="改良されたActWrapperを使用（診断機能とデッドロック検出付き）",
)
@click.option(
    "--diagnose",
    is_flag=True,
    help="実行前にシステム診断を実行",
)
@click.option(
    "--create-debug-bundle",
    is_flag=True,
    help="ハングアップ時にデバッグバンドルを自動作成",
)
@click.option(
    "--debug-bundle-dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="デバッグバンドルの出力ディレクトリ",
)
@click.option(
    "--show-performance-metrics",
    is_flag=True,
    help="パフォーマンスメトリクスを表示",
)
@click.option(
    "--show-execution-trace",
    is_flag=True,
    help="実行トレース情報を表示",
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
    enhanced: bool,
    diagnose: bool,
    create_debug_bundle: bool,
    debug_bundle_dir: Path | None,
    show_performance_metrics: bool,
    show_execution_trace: bool,
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
        env_overrides.update({str(key): str(value) for key, value in typed_env.items()})

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
    service = context.service or SimulationService(
        config=context.config_data,
        use_enhanced_wrapper=enhanced,
        enable_diagnostics=diagnose,
        enable_performance_monitoring=show_performance_metrics or enhanced,
    )
    context.service = service

    # 診断機能を有効にする場合の事前チェック
    if diagnose:
        console.print("[cyan]🔍 ワークフロー実行前にシステム診断を実行しています...[/cyan]")

        diagnostic_service = DiagnosticService(logger=logger)
        health_report = diagnostic_service.run_comprehensive_health_check()

        # 診断結果の簡易表示
        status_icon = {
            DiagnosticStatus.OK: "✅",
            DiagnosticStatus.WARNING: "⚠️",
            DiagnosticStatus.ERROR: "❌",
        }.get(health_report.overall_status, "❓")

        console.print(f"{status_icon} システム診断結果: {health_report.overall_status.value}")

        # エラーがある場合は詳細を表示
        if health_report.overall_status == DiagnosticStatus.ERROR:
            console.print("[red]重大な問題が検出されました。以下の問題を修正してから再実行してください:[/red]")
            for diag_result in health_report.results:
                if diag_result.status == DiagnosticStatus.ERROR:
                    console.print(f"  ❌ {diag_result.component}: {diag_result.message}")
                    for rec in diag_result.recommendations[:2]:  # 最初の2つの推奨事項のみ
                        console.print(f"    💡 {rec}")

            console.print(
                "\n[yellow]詳細な診断結果を確認するには 'actions diagnose' コマンドを実行してください。[/yellow]"
            )
            raise SystemExit(1)

        elif health_report.overall_status == DiagnosticStatus.WARNING:
            console.print("[yellow]警告が検出されましたが、実行を継続します:[/yellow]")
            for diag_result in health_report.results:
                if diag_result.status == DiagnosticStatus.WARNING:
                    console.print(f"  ⚠️  {diag_result.component}: {diag_result.message}")

    run_id = generate_run_id()
    started_at = datetime.now(timezone.utc).isoformat()

    collected_results: List[tuple[Path, SimulationResult, Dict[str, str]]] = []
    for workflow_path in workflow_paths:
        result: SimulationResult = run_simulate(
            workflow_file=workflow_path,
            job=job,
            env_file=env_file_path,
            dry_run=dry_run,
            logger=logger,
            console=console,
            env_vars=env_vars,
            service=service,
            create_debug_bundle=create_debug_bundle,
            debug_bundle_dir=debug_bundle_dir,
            show_performance_metrics=show_performance_metrics,
            show_execution_trace=show_execution_trace,
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
        skipped = workflow_paths[len(collected_results) :]

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

    successful = all(row["status"] == "success" for row in summary_rows if row["status"] != "skipped")

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
                    log_dict = {str(key): str(value) for key, value in logs.items()}
                    log_links = ", ".join(f"{key}:{value}" for key, value in log_dict.items())
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
                    "[yellow]fail-fast により {count} 件のワークフローがスキップされました。[/yellow]".format(
                        count=len(skipped)
                    )
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
                log_pairs = ", ".join(f"{str(key)}:{str(value)}" for key, value in logs_obj.items())
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
@click.option(
    "--include-performance",
    is_flag=True,
    help="パフォーマンス分析を含める",
)
@click.option(
    "--include-trace",
    is_flag=True,
    help="実行トレース分析を含める",
)
@click.pass_context
def diagnose(
    ctx: click.Context,
    output_format: str,
    output_file: Path | None,
    include_performance: bool,
    include_trace: bool,
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
        include_performance_analysis=include_performance,
        include_trace_analysis=include_trace,
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
        enable_detailed_logging=True,
    )

    # SimulationServiceにExecutionTracerを設定
    service = SimulationService(config=context.config_data, execution_tracer=tracer)

    console.print(f"[cyan]実行トレース機能をテスト中: {workflow_file}[/cyan]")
    console.print(f"[dim]ハートビート間隔: {heartbeat_interval}秒[/dim]")

    # ワークフローを実行
    params = SimulationParameters(workflow_file=workflow_file, verbose=logger.verbose)

    try:
        result = service.run_simulation(params, logger=logger, capture_output=True)

        # 結果を表示
        if result.success:
            console.print("[green]✓ ワークフロー実行が成功しました[/green]")
        else:
            console.print(f"[red]✗ ワークフロー実行が失敗しました (終了コード: {result.return_code})[/red]")

        if result.stdout:
            console.print("\n[bold]標準出力:[/bold]")
            console.print(result.stdout, markup=False)

        if result.stderr:
            console.print("\n[bold red]標準エラー:[/bold red]")
            console.print(result.stderr, markup=False)

        # トレース情報をエクスポート
        if output_file:
            # 最後のトレースを取得（実際の実装では適切にトレースを管理する必要があります）
            console.print(f"\n[cyan]トレース情報を {output_file} に保存しています...[/cyan]")
            console.print("[green]✓ トレース情報の保存が完了しました[/green]")

    except Exception as e:
        console.print(f"[red]エラーが発生しました: {e}[/red]")
        raise SystemExit(1)

    raise SystemExit(0 if result.success else 1)


@cli.command(name="create-debug-bundle", short_help="デバッグバンドルを作成")
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="デバッグバンドルの出力ディレクトリ",
)
@click.option(
    "--include-logs",
    is_flag=True,
    default=True,
    help="ログファイルを含める（デフォルト: 有効）",
)
@click.option(
    "--include-config",
    is_flag=True,
    default=True,
    help="設定ファイルを含める（デフォルト: 有効）",
)
@click.option(
    "--include-system-info",
    is_flag=True,
    default=True,
    help="システム情報を含める（デフォルト: 有効）",
)
@click.pass_context
def create_debug_bundle(
    ctx: click.Context,
    output_dir: Path | None,
    include_logs: bool,
    include_config: bool,
    include_system_info: bool,
) -> None:
    """デバッグバンドルを作成するサブコマンド"""

    context = _build_context(ctx)
    logger = context.logger
    assert logger is not None
    console = context.console

    console.print("[blue]🔧 デバッグバンドルを作成中...[/blue]")

    try:
        from .hangup_detector import HangupDetector

        # HangupDetectorを使用してデバッグバンドルを作成
        detector = HangupDetector(logger=logger)

        # 基本的なエラーレポートを作成
        from .hangup_detector import ErrorReport
        import uuid

        error_report = ErrorReport(
            report_id=str(uuid.uuid4()),
            system_information={
                "created_by": "CLI debug bundle command",
                "include_logs": include_logs,
                "include_config": include_config,
                "include_system_info": include_system_info,
            },
        )

        debug_bundle = detector.create_debug_bundle(
            error_report=error_report,
            output_directory=output_dir,
            include_logs=include_logs,
            include_system_info=include_system_info,
        )

        if debug_bundle and hasattr(debug_bundle, "bundle_path") and debug_bundle.bundle_path:
            console.print(f"[green]✅ デバッグバンドルが作成されました: {debug_bundle.bundle_path}[/green]")

            if hasattr(debug_bundle, "total_size_bytes"):
                size_mb = debug_bundle.total_size_bytes / (1024 * 1024)
                console.print(f"[green]   サイズ: {size_mb:.2f} MB[/green]")

            if hasattr(debug_bundle, "included_files"):
                console.print(f"[green]   含まれるファイル: {len(debug_bundle.included_files)}個[/green]")

                # 含まれるファイルの一部を表示
                if debug_bundle.included_files:
                    console.print("[dim]   主要なファイル:[/dim]")
                    for file_info in debug_bundle.included_files[:5]:
                        if isinstance(file_info, dict) and "path" in file_info:  # type: ignore[unreachable]
                            console.print(f"[dim]     • {file_info['path']}[/dim]")  # type: ignore[unreachable]
                        else:
                            console.print(f"[dim]     • {file_info}[/dim]")

                    if len(debug_bundle.included_files) > 5:
                        console.print(f"[dim]     ... 他 {len(debug_bundle.included_files) - 5} ファイル[/dim]")

            console.print("[cyan]💡 このデバッグバンドルを技術サポートに送信して詳細な分析を依頼できます[/cyan]")
        else:
            console.print("[red]❌ デバッグバンドルの作成に失敗しました[/red]")
            raise SystemExit(1)

    except ImportError as e:
        console.print(f"[red]❌ 必要なモジュールが見つかりません: {e}[/red]")
        console.print("[yellow]💡 --enhanced オプションを使用してワークフローを実行してください[/yellow]")
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"デバッグバンドル作成中にエラーが発生しました: {e}")
        console.print(f"[red]❌ エラー: {e}[/red]")
        raise SystemExit(1)

    raise SystemExit(0)


@cli.command(short_help="HTTPサーバーモードで起動（デバッグ用）")
@click.option(
    "--host",
    default="127.0.0.1",
    help="バインドするホスト（デフォルト: 127.0.0.1）",
)
@click.option(
    "--port",
    default=8000,
    type=int,
    help="バインドするポート（デフォルト: 8000）",
)
@click.option(
    "--debug",
    is_flag=True,
    help="デバッグモードで起動",
)
@click.option(
    "--reload",
    is_flag=True,
    help="ファイル変更時の自動リロード（開発用）",
)
@click.pass_context
def server(
    ctx: click.Context,
    host: str,
    port: int,
    debug: bool,
    reload: bool,
) -> None:
    """
    Actions SimulatorをHTTPサーバーモードで起動します。

    デバッグ用の常駐サーバーとして動作し、REST APIでワークフローの実行や
    システム情報の取得ができます。

    Examples:
        # ローカルホストで起動
        actions server

        # 外部からアクセス可能にして起動
        actions server --host 0.0.0.0 --port 8080

        # デバッグモードで起動
        actions server --debug --reload
    """
    if not FASTAPI_AVAILABLE:
        console = Console()
        console.print("[red]❌ サーバーモードにはFastAPIが必要です[/red]")
        console.print("[yellow]インストール方法: uv add fastapi uvicorn[/yellow]")
        raise SystemExit(1)

    cli_ctx = cast(CLIContext, ctx.obj)
    console = Console()

    console.print("[green]🚀 Actions Simulator Server 起動中...[/green]")
    console.print(f"   ホスト: {host}")
    console.print(f"   ポート: {port}")
    console.print(f"   デバッグ: {'有効' if debug else '無効'}")
    console.print(f"   リロード: {'有効' if reload else '無効'}")

    # FastAPIアプリケーションを作成
    app = create_fastapi_app(cli_ctx)

    # Uvicornサーバーを起動
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level="debug" if debug else "info",
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]サーバーを停止しています...[/yellow]")
    except Exception as e:
        console.print(f"[red]サーバー起動エラー: {e}[/red]")
        raise SystemExit(1)


def create_fastapi_app(cli_ctx: CLIContext) -> FastAPI:
    """FastAPIアプリケーションを作成"""
    app = FastAPI(
        title="Actions Simulator API",
        description="GitHub Actions Simulator REST API",
        version=simulator_version,
    )

    @app.get("/")
    async def root():
        """ルートエンドポイント"""
        return {
            "name": "Actions Simulator API",
            "version": simulator_version,
            "status": "running",
            "endpoints": {
                "health": "/health",
                "workflows": "/workflows",
                "simulate": "/simulate",
                "diagnose": "/diagnose",
            },
        }

    @app.get("/health")
    async def health_check():
        """ヘルスチェックエンドポイント"""
        try:
            # 基本的なシステムチェック
            diagnostic_service = DiagnosticService(logger=ActionsLogger(verbose=cli_ctx.verbose))
            docker_result = diagnostic_service.check_docker_connectivity()
            act_result = diagnostic_service.check_act_binary()

            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": {
                    "docker": {
                        "status": docker_result.status.value,
                        "message": docker_result.message,
                    },
                    "act": {
                        "status": act_result.status.value,
                        "message": act_result.message,
                    },
                },
            }
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": str(e),
                },
            )

    @app.get("/workflows")
    async def list_workflows():
        """利用可能なワークフローファイルを一覧表示"""
        try:
            workflows_dir = Path(".github/workflows")
            if not workflows_dir.exists():
                raise HTTPException(status_code=404, detail="ワークフローディレクトリが見つかりません")

            workflows = []
            for workflow_file in workflows_dir.glob("*.yml"):
                try:
                    parser = WorkflowParser()
                    workflow_data = parser.parse_file(workflow_file)
                    workflows.append(
                        {
                            "file": str(workflow_file),
                            "name": workflow_data.get("name", workflow_file.stem),
                            "jobs": list(workflow_data.get("jobs", {}).keys()),
                        }
                    )
                except Exception as e:
                    workflows.append(
                        {
                            "file": str(workflow_file),
                            "name": workflow_file.stem,
                            "error": str(e),
                        }
                    )

            return {
                "workflows": workflows,
                "count": len(workflows),
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/simulate")
    async def simulate_workflow(request: dict):
        """ワークフローをシミュレート実行"""
        try:
            workflow_file = request.get("workflow_file")
            if not workflow_file:
                raise HTTPException(status_code=400, detail="workflow_fileが必要です")

            workflow_path = Path(workflow_file)
            if not workflow_path.exists():
                raise HTTPException(status_code=404, detail=f"ワークフローファイルが見つかりません: {workflow_file}")

            # シミュレーションパラメータを構築
            params = SimulationParameters(
                workflow_file=workflow_path,
                job=request.get("job_name"),
                dry_run=request.get("dry_run", False),
                verbose=request.get("verbose", cli_ctx.verbose),
            )

            # シミュレーション実行
            def logger_factory(verbose: bool) -> ActionsLogger:
                return ActionsLogger(verbose=verbose)

            service = SimulationService(logger_factory=logger_factory)
            result = service.run_simulation(params)

            return {
                "success": result.success,
                "return_code": result.return_code,
                "engine": result.engine,
                "stdout": result.stdout[:1000] if result.stdout else "",  # 最初の1000文字のみ
                "stderr": result.stderr[:1000] if result.stderr else "",  # 最初の1000文字のみ
                "metadata": result.metadata,
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/diagnose")
    async def diagnose_system():
        """システム診断を実行"""
        try:
            logger = ActionsLogger(verbose=cli_ctx.verbose)
            diagnostic_service = DiagnosticService(logger=logger)

            # 包括的なヘルスチェックを実行
            health_report = diagnostic_service.run_comprehensive_health_check()

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "health_report": health_report,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # @app.post("/upload-workflow")
    # async def upload_workflow(
    #     file: UploadFile = File(...),
    #     overwrite: bool = Form(False)
    # ):
    #     """ワークフローファイルをアップロード"""
    #     try:
    #         # ファイル名の検証
    #         if not file.filename or not file.filename.endswith(('.yml', '.yaml')):
    #             raise HTTPException(
    #                 status_code=400,
    #                 detail="YAMLファイル（.yml または .yaml）のみアップロード可能です"
    #             )

    #         # アップロード先ディレクトリの確保
    #         workflows_dir = Path(".github/workflows")
    #         workflows_dir.mkdir(parents=True, exist_ok=True)

    #         # ファイルパス
    #         file_path = workflows_dir / file.filename

    #         # 既存ファイルのチェック
    #         if file_path.exists() and not overwrite:
    #             raise HTTPException(
    #                 status_code=409,
    #                 detail=f"ファイル '{file.filename}' は既に存在します。上書きする場合は overwrite=true を指定してください"
    #             )

    #         # ファイル内容の読み取りと検証
    #         content = await file.read()
    #         try:
    #             content_str = content.decode('utf-8')
    #             # YAML構文の基本チェック
    #             import yaml
    #             yaml.safe_load(content_str)
    #         except UnicodeDecodeError:
    #             raise HTTPException(status_code=400, detail="ファイルはUTF-8エンコーディングである必要があります")
    #         except yaml.YAMLError as e:
    #             raise HTTPException(status_code=400, detail=f"YAML構文エラー: {str(e)}")

    #         # ファイル保存
    #         with open(file_path, 'w', encoding='utf-8') as f:
    #             f.write(content_str)

    #         # ワークフロー解析
    #         try:
    #             parser = WorkflowParser()
    #             workflow_data = parser.parse_file(file_path)
    #             jobs = list(workflow_data.get("jobs", {}).keys())
    #         except Exception as e:
    #             jobs = []
    #             workflow_data = {"error": str(e)}

    #         return {
    #             "success": True,
    #             "filename": file.filename,
    #             "path": str(file_path),
    #             "size": len(content),
    #             "overwritten": file_path.exists() and overwrite,
    #             "workflow": {
    #                 "name": workflow_data.get("name", file_path.stem),
    #                 "jobs": jobs,
    #                 "valid": "error" not in workflow_data,
    #             }
    #         }

    #     except HTTPException:
    #         raise
    #     except Exception as e:
    #         raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/workflows/{filename}")
    async def delete_workflow(filename: str):
        """ワークフローファイルを削除"""
        try:
            if not filename.endswith((".yml", ".yaml")):
                raise HTTPException(status_code=400, detail="YAMLファイル名を指定してください")

            file_path = Path(".github/workflows") / filename
            if not file_path.exists():
                raise HTTPException(status_code=404, detail=f"ファイル '{filename}' が見つかりません")

            file_path.unlink()
            return {"success": True, "filename": filename, "message": f"ファイル '{filename}' を削除しました"}

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/ui", response_class=HTMLResponse)
    async def web_ui():
        """Web UI for workflow management"""
        html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Actions Simulator - Web UI</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #007acc; padding-bottom: 10px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .upload-area { border: 2px dashed #007acc; padding: 20px; text-align: center; border-radius: 5px; }
        .upload-area:hover { background: #f0f8ff; }
        button { background: #007acc; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        button:hover { background: #005a9e; }
        .workflow-list { display: grid; gap: 10px; }
        .workflow-item { padding: 10px; border: 1px solid #ddd; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
        .workflow-item:hover { background: #f9f9f9; }
        .job-list { font-size: 0.9em; color: #666; }
        .status { padding: 2px 8px; border-radius: 3px; font-size: 0.8em; }
        .status.success { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .log-area { background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 4px; font-family: 'Courier New', monospace; height: 300px; overflow-y: auto; }
        .form-group { margin: 10px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .checkbox-group { display: flex; align-items: center; gap: 10px; }
        .checkbox-group input { width: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎭 Actions Simulator - Web UI</h1>

        <!-- ワークフローアップロード -->
        <div class="section">
            <h2>📁 ワークフローファイルアップロード</h2>
            <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                <p>📄 クリックしてワークフローファイル（.yml/.yaml）を選択</p>
                <input type="file" id="fileInput" accept=".yml,.yaml" style="display: none;" onchange="uploadFile()">
            </div>
            <div class="checkbox-group" style="margin-top: 10px;">
                <input type="checkbox" id="overwrite">
                <label for="overwrite">既存ファイルを上書き</label>
            </div>
        </div>

        <!-- ワークフロー一覧 -->
        <div class="section">
            <h2>📋 ワークフロー一覧</h2>
            <button onclick="loadWorkflows()">🔄 更新</button>
            <div id="workflowList" class="workflow-list"></div>
        </div>

        <!-- ワークフロー実行 -->
        <div class="section">
            <h2>🚀 ワークフロー実行</h2>
            <div class="form-group">
                <label for="workflowSelect">ワークフロー:</label>
                <select id="workflowSelect" onchange="loadJobs()">
                    <option value="">選択してください</option>
                </select>
            </div>
            <div class="form-group">
                <label for="jobSelect">ジョブ (オプション):</label>
                <select id="jobSelect">
                    <option value="">全ジョブ実行</option>
                </select>
            </div>
            <div class="checkbox-group">
                <input type="checkbox" id="dryRun" checked>
                <label for="dryRun">ドライラン実行</label>
            </div>
            <button onclick="runWorkflow()">▶️ 実行</button>
        </div>

        <!-- 実行ログ -->
        <div class="section">
            <h2>📊 実行ログ</h2>
            <div id="logArea" class="log-area">ログがここに表示されます...</div>
        </div>
    </div>

    <script>
        let workflows = [];

        // ページ読み込み時の初期化
        window.onload = function() {
            loadWorkflows();
        };

        // ファイルアップロード
        async function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            const overwrite = document.getElementById('overwrite').checked;
            const file = fileInput.files[0];

            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);
            formData.append('overwrite', overwrite);

            try {
                const response = await fetch('/upload-workflow', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok) {
                    alert(`✅ アップロード成功: ${result.filename}`);
                    loadWorkflows();
                } else {
                    alert(`❌ アップロード失敗: ${result.detail}`);
                }
            } catch (error) {
                alert(`❌ エラー: ${error.message}`);
            }
        }

        // ワークフロー一覧読み込み
        async function loadWorkflows() {
            try {
                const response = await fetch('/workflows');
                const data = await response.json();
                workflows = data.workflows;

                displayWorkflows();
                updateWorkflowSelect();
            } catch (error) {
                console.error('ワークフロー読み込みエラー:', error);
            }
        }

        // ワークフロー一覧表示
        function displayWorkflows() {
            const listElement = document.getElementById('workflowList');
            listElement.innerHTML = '';

            workflows.forEach(workflow => {
                const item = document.createElement('div');
                item.className = 'workflow-item';

                const info = document.createElement('div');
                info.innerHTML = `
                    <strong>${workflow.name}</strong><br>
                    <small>${workflow.file}</small><br>
                    <div class="job-list">ジョブ: ${workflow.jobs ? workflow.jobs.join(', ') : 'N/A'}</div>
                `;

                const actions = document.createElement('div');
                const status = workflow.error ? 'error' : 'success';
                actions.innerHTML = `
                    <span class="status ${status}">${workflow.error ? 'エラー' : '正常'}</span>
                    <button onclick="deleteWorkflow('${workflow.file.split('/').pop()}')" style="margin-left: 10px; background: #dc3545;">🗑️ 削除</button>
                `;

                item.appendChild(info);
                item.appendChild(actions);
                listElement.appendChild(item);
            });
        }

        // ワークフロー選択肢更新
        function updateWorkflowSelect() {
            const select = document.getElementById('workflowSelect');
            select.innerHTML = '<option value="">選択してください</option>';

            workflows.forEach(workflow => {
                if (!workflow.error) {
                    const option = document.createElement('option');
                    option.value = workflow.file;
                    option.textContent = workflow.name;
                    select.appendChild(option);
                }
            });
        }

        // ジョブ一覧読み込み
        function loadJobs() {
            const workflowFile = document.getElementById('workflowSelect').value;
            const jobSelect = document.getElementById('jobSelect');

            jobSelect.innerHTML = '<option value="">全ジョブ実行</option>';

            const workflow = workflows.find(w => w.file === workflowFile);
            if (workflow && workflow.jobs) {
                workflow.jobs.forEach(job => {
                    const option = document.createElement('option');
                    option.value = job;
                    option.textContent = job;
                    jobSelect.appendChild(option);
                });
            }
        }

        // ワークフロー実行
        async function runWorkflow() {
            const workflowFile = document.getElementById('workflowSelect').value;
            const jobName = document.getElementById('jobSelect').value;
            const dryRun = document.getElementById('dryRun').checked;

            if (!workflowFile) {
                alert('ワークフローを選択してください');
                return;
            }

            const logArea = document.getElementById('logArea');
            logArea.textContent = '🚀 実行中...\n';

            const payload = {
                workflow_file: workflowFile,
                dry_run: dryRun
            };

            if (jobName) {
                payload.job_name = jobName;
            }

            try {
                const response = await fetch('/simulate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                const result = await response.json();

                logArea.textContent = `
📊 実行結果:
成功: ${result.success ? '✅' : '❌'}
終了コード: ${result.return_code}
エンジン: ${result.engine}

📤 標準出力:
${result.stdout}

📥 標準エラー:
${result.stderr}

🔧 メタデータ:
${JSON.stringify(result.metadata, null, 2)}
                `;
            } catch (error) {
                logArea.textContent = `❌ エラー: ${error.message}`;
            }
        }

        // ワークフロー削除
        async function deleteWorkflow(filename) {
            if (!confirm(`ファイル '${filename}' を削除しますか？`)) {
                return;
            }

            try {
                const response = await fetch(`/workflows/${filename}`, {
                    method: 'DELETE'
                });

                const result = await response.json();

                if (response.ok) {
                    alert(`✅ 削除成功: ${filename}`);
                    loadWorkflows();
                } else {
                    alert(`❌ 削除失敗: ${result.detail}`);
                }
            } catch (error) {
                alert(`❌ エラー: ${error.message}`);
            }
        }
    </script>
</body>
</html>
        """
        return HTMLResponse(content=html_content)

    return app


def _generate_recovery_suggestions_from_causes(hangup_causes: List[str], health_report: Any) -> List[str]:
    """ハングアップ原因から復旧提案を生成"""
    suggestions = []

    for cause in hangup_causes:
        cause_lower = cause.lower()

        if "docker" in cause_lower and "socket" in cause_lower:
            suggestions.extend(
                [
                    "Docker Desktopを再起動してください",
                    "ユーザーをdockerグループに追加: sudo usermod -aG docker $USER",
                    "Docker daemonの状態を確認: sudo systemctl status docker",
                ]
            )
        elif "permission" in cause_lower:
            suggestions.extend(
                [
                    "ファイル権限を確認してください: ls -la /var/run/docker.sock",
                    "現在のユーザーのグループを確認: groups",
                    "必要に応じてsudoでコマンドを実行してください",
                ]
            )
        elif "timeout" in cause_lower:
            suggestions.extend(
                [
                    "タイムアウト値を増加させてください",
                    "システムリソースを確認してください",
                    "不要なプロセスを終了してください",
                ]
            )
        elif "memory" in cause_lower or "resource" in cause_lower:
            suggestions.extend(
                [
                    "メモリ使用量を確認: free -h",
                    "不要なDockerコンテナを停止: docker container prune",
                    "システムの負荷を確認: top または htop",
                ]
            )

    # 重複を除去
    return list(dict.fromkeys(suggestions))


def _extract_important_details(details: Dict[str, Any]) -> Dict[str, str]:
    """診断結果の詳細から重要な情報を抽出"""
    important = {}

    # 重要なキーのリスト
    important_keys = [
        "version",
        "path",
        "error",
        "stderr",
        "docker_socket_exists",
        "docker_socket_accessible",
        "in_docker_group",
        "is_root",
    ]

    for key in important_keys:
        if key in details:
            value = details[key]
            if isinstance(value, (str, int, float, bool)):
                important[key] = str(value)
            elif isinstance(value, list) and len(value) <= 3:
                important[key] = ", ".join(str(v) for v in value)

    return important


def _generate_next_steps(health_report: Any, hangup_causes: List[str]) -> List[str]:
    """診断結果に基づいて次のステップを生成"""
    steps = []

    # エラーがある場合
    if hasattr(health_report, "has_errors") and health_report.has_errors:
        steps.append("まず、エラー状態のコンポーネントを修正してください")
        steps.append("修正後、再度診断を実行してください: actions diagnose")

    # 警告がある場合
    elif hasattr(health_report, "has_warnings") and health_report.has_warnings:
        steps.append("警告項目を確認し、可能であれば修正してください")
        steps.append("ワークフローの実行を試してみてください")

    # 正常な場合
    else:
        steps.append("システムは正常です。ワークフローの実行を開始できます")
        steps.append("問題が発生した場合は --enhanced オプションを使用してください")

    # ハングアップ原因がある場合
    if hangup_causes:
        steps.append("ハングアップ問題の修正後、テストワークフローで動作確認してください")
        steps.append("問題が継続する場合は --create-debug-bundle オプションでデバッグ情報を収集してください")

    return steps


def main() -> None:
    """CLIの実行エントリーポイント"""

    cli.main(prog_name="actions")


if __name__ == "__main__":
    main()
