"""
GitHub Actions Simulator - ハングアップ検出器
特定のタイプのハングアップ条件を識別し、詳細なエラーレポートと
デバッグバンドル生成機能を提供します。
"""

import json
import os
import subprocess
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class HangupType(Enum):
    """ハングアップの種類"""
    DOCKER_SOCKET_ISSUE = "docker_socket_issue"
    SUBPROCESS_DEADLOCK = "subprocess_deadlock"
    TIMEOUT_PROBLEM = "timeout_problem"
    PERMISSION_ISSUE = "permission_issue"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CONTAINER_COMMUNICATION = "container_communication"


class HangupSeverity(Enum):
    """ハングアップの重要度"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class HangupIssue:
    """ハングアップ問題の詳細"""
    issue_type: HangupType
    severity: HangupSeverity
    title: str
    description: str
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evidence: Dict[str, Any] = field(default_factory=dict)
    root_cause: Optional[str] = None
    impact_assessment: str = ""
    recommendations: List[str] = field(default_factory=list)
    fix_commands: List[str] = field(default_factory=list)
    confidence_score: float = 0.0  # 0.0-1.0


@dataclass
class HangupAnalysis:
    """ハングアップ分析結果"""
    analysis_id: str
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    issues: List[HangupIssue] = field(default_factory=list)
    primary_cause: Optional[HangupIssue] = None
    secondary_causes: List[HangupIssue] = field(default_factory=list)
    system_state: Dict[str, Any] = field(default_factory=dict)
    execution_context: Dict[str, Any] = field(default_factory=dict)
    recovery_suggestions: List[str] = field(default_factory=list)
    prevention_measures: List[str] = field(default_factory=list)


@dataclass
class ErrorReport:
    """詳細エラーレポート"""
    report_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hangup_analysis: Optional[HangupAnalysis] = None
    diagnostic_results: List[Any] = field(default_factory=list)
    execution_trace: Optional[Any] = None
    system_information: Dict[str, Any] = field(default_factory=dict)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    docker_status: Dict[str, Any] = field(default_factory=dict)
    troubleshooting_guide: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)


@dataclass
class DebugBundle:
    """デバッグバンドル情報"""
    bundle_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    bundle_path: Optional[Path] = None
    included_files: List[str] = field(default_factory=list)
    file_sizes: Dict[str, int] = field(default_factory=dict)
    total_size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class HangupDetector:
    """
    特定のタイプのハングアップ条件を識別し、
    詳細なエラーレポートとデバッグバンドル生成を行うクラス
    """

    def __init__(
        self,
        logger=None,
        diagnostic_service=None,
        execution_tracer=None,
        confidence_threshold: float = 0.7
    ):
        """
        HangupDetectorを初期化

        Args:
            logger: ログ出力用のロガー
            diagnostic_service: 診断サービス
            execution_tracer: 実行トレーサー
            confidence_threshold: 問題検出の信頼度閾値
        """
        self.logger = logger
        self.diagnostic_service = diagnostic_service
        self.execution_tracer = execution_tracer
        self.confidence_threshold = confidence_threshold

    def detect_docker_socket_issues(self) -> List[HangupIssue]:
        """
        Dockerソケット関連の問題を検出

        Returns:
            List[HangupIssue]: 検出されたDockerソケット問題のリスト
        """
        if self.logger:
            self.logger.debug("Dockerソケット問題を検出中...")

        issues = []

        try:
            # Dockerソケットの存在確認
            docker_socket = Path("/var/run/docker.sock")
            if not docker_socket.exists():
                issues.append(HangupIssue(
                    issue_type=HangupType.DOCKER_SOCKET_ISSUE,
                    severity=HangupSeverity.CRITICAL,
                    title="Dockerソケットが見つかりません",
                    description="Docker daemonとの通信に必要なソケットファイルが存在しません",
                    evidence={"socket_path": str(docker_socket), "exists": False},
                    root_cause="Docker daemonが起動していないか、ソケットパスが間違っています",
                    impact_assessment="GitHub Actionsシミュレーションが実行できません",
                    recommendations=[
                        "Docker Desktopまたは Docker Engineを起動してください",
                        "Docker daemonが正常に動作しているか確認してください"
                    ],
                    fix_commands=[
                        "sudo systemctl start docker",
                        "docker info"
                    ],
                    confidence_score=0.95
                ))

            # Docker daemon接続テスト
            try:
                result = subprocess.run(
                    ["docker", "version", "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode != 0:
                    issues.append(HangupIssue(
                        issue_type=HangupType.DOCKER_SOCKET_ISSUE,
                        severity=HangupSeverity.HIGH,
                        title="Docker daemon接続エラー",
                        description="Docker daemonとの通信に失敗しました",
                        evidence={
                            "command": "docker version",
                            "returncode": result.returncode,
                            "stderr": result.stderr[:500]
                        },
                        root_cause="Docker daemonが応答していないか、通信エラーが発生しています",
                        impact_assessment="すべてのDocker操作が失敗します",
                        recommendations=[
                            "Docker daemonの状態を確認してください",
                            "Docker Desktopを再起動してください"
                        ],
                        fix_commands=[
                            "docker system info",
                            "sudo systemctl restart docker"
                        ],
                        confidence_score=0.85
                    ))

            except subprocess.TimeoutExpired:
                issues.append(HangupIssue(
                    issue_type=HangupType.DOCKER_SOCKET_ISSUE,
                    severity=HangupSeverity.HIGH,
                    title="Docker daemon応答タイムアウト",
                    description="Docker daemonからの応答がタイムアウトしました",
                    evidence={"timeout_seconds": 10},
                    root_cause="Docker daemonの負荷が高いか、システムリソースが不足しています",
                    impact_assessment="Docker操作が非常に遅くなるか、タイムアウトで失敗します",
                    recommendations=[
                        "システムリソース（CPU、メモリ）を確認してください",
                        "実行中のコンテナ数を確認してください"
                    ],
                    fix_commands=[
                        "docker ps",
                        "docker system df"
                    ],
                    confidence_score=0.80
                ))

        except Exception as e:
            if self.logger:
                self.logger.error(f"Dockerソケット問題検出中にエラーが発生しました: {e}")

        return issues

    def analyze_hangup_conditions(
        self,
        execution_trace=None,
        diagnostic_results=None
    ) -> HangupAnalysis:
        """
        包括的なハングアップ条件分析を実行

        Args:
            execution_trace: 実行トレース情報
            diagnostic_results: 診断結果

        Returns:
            HangupAnalysis: ハングアップ分析結果
        """
        analysis_id = f"hangup_analysis_{int(time.time() * 1000)}"
        if self.logger:
            self.logger.info(f"包括的なハングアップ分析を開始: {analysis_id}")

        analysis = HangupAnalysis(analysis_id=analysis_id)

        try:
            # Docker関連問題を検出
            docker_issues = self.detect_docker_socket_issues()

            # 信頼度でフィルタリング
            filtered_issues = [
                issue for issue in docker_issues
                if issue.confidence_score >= self.confidence_threshold
            ]

            analysis.issues = filtered_issues

            # 主要原因を特定
            if filtered_issues:
                sorted_issues = sorted(
                    filtered_issues,
                    key=lambda x: (x.severity.value, x.confidence_score),
                    reverse=True
                )
                analysis.primary_cause = sorted_issues[0]

            # システム状態の収集
            analysis.system_state = {"timestamp": datetime.now(timezone.utc).isoformat()}

            # 復旧提案の生成
            analysis.recovery_suggestions = [
                "Docker Desktopまたは Docker Engineが実行されていることを確認してください",
                "システムリソース（CPU、メモリ、ディスク容量）を確認してください"
            ]

            analysis.end_time = datetime.now(timezone.utc).isoformat()

            if self.logger:
                self.logger.info(f"ハングアップ分析完了: {len(filtered_issues)}個の問題を検出")

        except Exception as e:
            if self.logger:
                self.logger.error(f"ハングアップ分析中にエラーが発生しました: {e}")
            analysis.end_time = datetime.now(timezone.utc).isoformat()

        return analysis

    def generate_detailed_error_report(
        self,
        hangup_analysis: Optional[HangupAnalysis] = None,
        diagnostic_results=None,
        execution_trace=None
    ) -> ErrorReport:
        """
        詳細なエラーレポートを生成

        Args:
            hangup_analysis: ハングアップ分析結果
            diagnostic_results: 診断結果
            execution_trace: 実行トレース

        Returns:
            ErrorReport: 詳細エラーレポート
        """
        report_id = f"error_report_{int(time.time() * 1000)}"
        if self.logger:
            self.logger.info(f"詳細エラーレポートを生成中: {report_id}")

        report = ErrorReport(
            report_id=report_id,
            hangup_analysis=hangup_analysis,
            diagnostic_results=diagnostic_results or [],
            execution_trace=execution_trace
        )

        try:
            # システム情報の収集
            report.system_information = {"os": os.name}

            # 環境変数の収集
            relevant_vars = ["DOCKER_HOST", "PATH", "HOME", "USER"]
            report.environment_variables = {var: os.environ.get(var, "") for var in relevant_vars}

            # トラブルシューティングガイドの生成
            report.troubleshooting_guide = [
                "## トラブルシューティングガイド",
                "### 1. 基本確認事項",
                "- Docker Desktopまたは Docker Engineが起動していることを確認"
            ]

            # 次のステップの提案
            report.next_steps = [
                "1. このエラーレポートを確認し、主要な問題を特定してください",
                "2. 推奨される修正手順を実行してください"
            ]

            if self.logger:
                self.logger.info(f"詳細エラーレポート生成完了: {report_id}")

        except Exception as e:
            if self.logger:
                self.logger.error(f"エラーレポート生成中にエラーが発生しました: {e}")

        return report

    def create_debug_bundle(
        self,
        error_report: ErrorReport,
        output_directory: Optional[Path] = None,
        include_logs: bool = True,
        include_system_info: bool = True,
        include_docker_info: bool = True
    ) -> DebugBundle:
        """
        複雑な問題のトラブルシューティング用デバッグバンドルを生成

        Args:
            error_report: エラーレポート
            output_directory: 出力ディレクトリ
            include_logs: ログファイルを含めるかどうか
            include_system_info: システム情報を含めるかどうか
            include_docker_info: Docker情報を含めるかどうか

        Returns:
            DebugBundle: 生成されたデバッグバンドル情報
        """
        bundle_id = f"debug_bundle_{int(time.time() * 1000)}"
        if self.logger:
            self.logger.info(f"デバッグバンドルを作成中: {bundle_id}")

        if output_directory is None:
            output_directory = Path.cwd() / "debug_bundles"

        output_directory.mkdir(parents=True, exist_ok=True)
        bundle_path = output_directory / f"{bundle_id}.zip"

        bundle = DebugBundle(
            bundle_id=bundle_id,
            bundle_path=bundle_path
        )

        try:
            with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # エラーレポートをJSON形式で追加
                report_dict = {
                    "report_id": error_report.report_id,
                    "timestamp": error_report.timestamp,
                    "system_information": error_report.system_information,
                    "environment_variables": error_report.environment_variables,
                    "troubleshooting_guide": error_report.troubleshooting_guide,
                    "next_steps": error_report.next_steps
                }

                if error_report.hangup_analysis:
                    report_dict["hangup_analysis"] = {
                        "analysis_id": error_report.hangup_analysis.analysis_id,
                        "issues_count": len(error_report.hangup_analysis.issues),
                        "primary_cause": error_report.hangup_analysis.primary_cause.title if error_report.hangup_analysis.primary_cause else None
                    }

                report_content = json.dumps(report_dict, ensure_ascii=False, indent=2)
                zipf.writestr(f"{bundle_id}/error_report.json", report_content)
                bundle.included_files.append("error_report.json")

                # メタデータを追加
                metadata = {
                    "bundle_id": bundle_id,
                    "created_at": bundle.created_at,
                    "error_report_id": error_report.report_id,
                    "file_count": len(bundle.included_files)
                }
                bundle.metadata = metadata

                metadata_content = json.dumps(metadata, ensure_ascii=False, indent=2)
                zipf.writestr(f"{bundle_id}/metadata.json", metadata_content)
                bundle.included_files.append("metadata.json")

            # バンドル統計を計算
            bundle.total_size_bytes = bundle_path.stat().st_size

            if self.logger:
                self.logger.info(
                    f"デバッグバンドル作成完了: {bundle_path} "
                    f"({bundle.total_size_bytes} bytes, {len(bundle.included_files)} files)"
                )

        except Exception as e:
            if self.logger:
                self.logger.error(f"デバッグバンドル作成中にエラーが発生しました: {e}")
            if bundle_path.exists():
                bundle_path.unlink()
            bundle.bundle_path = None

        return bundle
