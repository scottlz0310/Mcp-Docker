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
        confidence_threshold: float = 0.7,
        max_log_lines: int = 1000
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
        self.max_log_lines = max_log_lines
        self._detection_patterns = self._initialize_detection_patterns()
        self._known_issues_db = self._initialize_known_issues_db()

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
                return issues  # ソケットが存在しない場合は早期リターン

            # Docker daemon基本接続テスト
            try:
                # 最初にDocker daemonの基本的な応答をテスト
                result = subprocess.run(
                    ["docker", "info"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # 次にバージョン情報を取得
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
        start_time = time.time()

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

            # 予防策の生成
            analysis.prevention_measures = self._generate_prevention_measures(analysis)

            analysis.end_time = datetime.now(timezone.utc).isoformat()
            analysis.duration_ms = (time.time() - start_time) * 1000

            if self.logger:
                self.logger.info(f"ハングアップ分析完了: {len(filtered_issues)}個の問題を検出")

        except Exception as e:
            if self.logger:
                self.logger.error(f"ハングアップ分析中にエラーが発生しました: {e}")
            analysis.end_time = datetime.now(timezone.utc).isoformat()
            analysis.duration_ms = (time.time() - start_time) * 1000

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

    def detect_subprocess_deadlock(self, execution_trace=None) -> List[HangupIssue]:
        """
        サブプロセスデッドロック関連の問題を検出

        Args:
            execution_trace: 実行トレース情報

        Returns:
            List[HangupIssue]: 検出されたサブプロセスデッドロック問題のリスト
        """
        if self.logger:
            self.logger.debug("サブプロセスデッドロック問題を検出中...")

        issues = []

        if execution_trace is None:
            return issues

        try:
            # 長時間実行プロセスの検出
            if hasattr(execution_trace, 'process_traces'):
                for process_trace in execution_trace.process_traces:
                    if hasattr(process_trace, 'start_time'):
                        from datetime import datetime, timezone, timedelta
                        import time
                        
                        # start_timeが文字列の場合はdatetimeに変換
                        if isinstance(process_trace.start_time, str):
                            start_time = datetime.fromisoformat(process_trace.start_time.replace('Z', '+00:00'))
                        else:
                            start_time = process_trace.start_time
                        
                        current_time = datetime.now(timezone.utc)
                        duration = current_time - start_time
                        
                        # 5分以上実行されているプロセスを検出
                        if duration > timedelta(minutes=5):
                            issues.append(HangupIssue(
                                issue_type=HangupType.SUBPROCESS_DEADLOCK,
                                severity=HangupSeverity.HIGH,
                                title="長時間実行プロセスが応答しません",
                                description=f"プロセス {process_trace.command} が {duration.total_seconds():.0f}秒間実行されています",
                                evidence={
                                    "command": process_trace.command,
                                    "pid": getattr(process_trace, 'pid', None),
                                    "duration_seconds": duration.total_seconds()
                                },
                                root_cause="プロセスがデッドロック状態またはハングアップしている可能性があります",
                                impact_assessment="ワークフロー実行が完了しません",
                                recommendations=[
                                    "プロセスを強制終了してください",
                                    "Docker daemonの状態を確認してください"
                                ],
                                confidence_score=0.8
                            ))

        except Exception as e:
            if self.logger:
                self.logger.error(f"サブプロセスデッドロック検出中にエラーが発生しました: {e}")

        return issues

    def detect_timeout_problems(self, execution_trace=None) -> List[HangupIssue]:
        """
        タイムアウト関連の問題を検出

        Args:
            execution_trace: 実行トレース情報

        Returns:
            List[HangupIssue]: 検出されたタイムアウト問題のリスト
        """
        if self.logger:
            self.logger.debug("タイムアウト問題を検出中...")

        issues = []

        try:
            # 環境変数のタイムアウト設定をチェック
            timeout_env = os.environ.get('ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS')
            if timeout_env:
                try:
                    timeout_value = int(timeout_env)
                    
                    if timeout_value < 0:
                        issues.append(HangupIssue(
                            issue_type=HangupType.TIMEOUT_PROBLEM,
                            severity=HangupSeverity.MEDIUM,
                            title="無効なタイムアウト設定",
                            description=f"タイムアウト値が負の数です: {timeout_value}",
                            evidence={"timeout_value": timeout_value, "env_var": timeout_env},
                            root_cause="環境変数の設定が不正です",
                            impact_assessment="タイムアウト処理が正常に動作しません",
                            recommendations=[
                                "ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS環境変数を正の値に設定してください"
                            ],
                            confidence_score=0.95
                        ))
                    elif timeout_value < 120:  # 2分未満
                        issues.append(HangupIssue(
                            issue_type=HangupType.TIMEOUT_PROBLEM,
                            severity=HangupSeverity.LOW,
                            title="タイムアウト値が短すぎます",
                            description=f"タイムアウト値が短すぎる可能性があります: {timeout_value}秒",
                            evidence={"timeout_value": timeout_value},
                            root_cause="タイムアウト値が短すぎてワークフローが完了できません",
                            impact_assessment="正常なワークフローも途中で終了する可能性があります",
                            recommendations=[
                                "タイムアウト値を300秒以上に設定することを推奨します"
                            ],
                            confidence_score=0.7
                        ))
                        
                except ValueError:
                    issues.append(HangupIssue(
                        issue_type=HangupType.TIMEOUT_PROBLEM,
                        severity=HangupSeverity.HIGH,
                        title="無効なタイムアウト設定",
                        description=f"タイムアウト値が数値ではありません: {timeout_env}",
                        evidence={"env_var": timeout_env},
                        root_cause="環境変数の値が数値として解析できません",
                        impact_assessment="タイムアウト処理が正常に動作しません",
                        recommendations=[
                            "ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS環境変数を数値に設定してください"
                        ],
                        confidence_score=0.95
                    ))

            # 実行トレースからハングポイントを検出
            if execution_trace and hasattr(execution_trace, 'hang_point') and execution_trace.hang_point:
                issues.append(HangupIssue(
                    issue_type=HangupType.TIMEOUT_PROBLEM,
                    severity=HangupSeverity.HIGH,
                    title="ハングアップを検出しました",
                    description=f"実行がハングしています: {execution_trace.hang_point}",
                    evidence={"hang_point": execution_trace.hang_point},
                    root_cause="特定のポイントで実行が停止しています",
                    impact_assessment="ワークフロー実行が完了しません",
                    recommendations=[
                        "ハングポイントでの処理を確認してください",
                        "Docker daemonの状態を確認してください"
                    ],
                    confidence_score=0.85
                ))

        except Exception as e:
            if self.logger:
                self.logger.error(f"タイムアウト問題検出中にエラーが発生しました: {e}")

        return issues

    def detect_permission_issues(self) -> List[HangupIssue]:
        """
        権限関連の問題を検出

        Returns:
            List[HangupIssue]: 検出された権限問題のリスト
        """
        if self.logger:
            self.logger.debug("権限問題を検出中...")

        issues = []

        try:
            # Dockerグループの確認
            try:
                result = subprocess.run(
                    ["groups"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    groups = result.stdout.strip().split()
                    if "docker" not in groups:
                        issues.append(HangupIssue(
                            issue_type=HangupType.PERMISSION_ISSUE,
                            severity=HangupSeverity.HIGH,
                            title="dockerグループに属していません",
                            description="現在のユーザーがdockerグループに属していません",
                            evidence={"user_groups": groups},
                            root_cause="Docker daemonへのアクセス権限がありません",
                            impact_assessment="Docker操作が失敗します",
                            recommendations=[
                                "ユーザーをdockerグループに追加してください: sudo usermod -aG docker $USER",
                                "ログアウト・ログインしてグループ変更を反映してください"
                            ],
                            confidence_score=0.9
                        ))
                        
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

            # 作業ディレクトリの書き込み権限確認
            current_dir = Path.cwd()
            if not os.access(current_dir, os.W_OK):
                issues.append(HangupIssue(
                    issue_type=HangupType.PERMISSION_ISSUE,
                    severity=HangupSeverity.MEDIUM,
                    title="作業ディレクトリへの書き込み権限がありません",
                    description=f"現在のディレクトリ {current_dir} への書き込み権限がありません",
                    evidence={"directory": str(current_dir), "writable": False},
                    root_cause="ディレクトリの権限設定が不適切です",
                    impact_assessment="一時ファイルの作成やログ出力が失敗する可能性があります",
                    recommendations=[
                        "ディレクトリの権限を確認してください",
                        "書き込み可能なディレクトリに移動してください"
                    ],
                    confidence_score=0.8
                ))

        except Exception as e:
            if self.logger:
                self.logger.error(f"権限問題検出中にエラーが発生しました: {e}")

        return issues

    def _collect_detailed_system_info(self) -> Dict[str, Any]:
        """詳細なシステム情報を収集"""
        system_info = {}
        
        try:
            # OS情報
            system_info["os"] = os.name
            system_info["platform"] = os.uname() if hasattr(os, 'uname') else "unknown"
            
            # 環境変数
            relevant_vars = ["DOCKER_HOST", "PATH", "HOME", "USER", "ACTIONS_SIMULATOR_ACT_TIMEOUT_SECONDS"]
            system_info["environment"] = {var: os.environ.get(var, "") for var in relevant_vars}
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"システム情報収集中にエラー: {e}")
                
        return system_info

    def _collect_docker_status(self) -> Dict[str, Any]:
        """Docker状態情報を収集"""
        docker_status = {}
        
        try:
            # Docker version
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                docker_status["version"] = result.stdout.strip()
                
            # Docker info
            result = subprocess.run(
                ["docker", "info", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                try:
                    docker_status["info"] = json.loads(result.stdout)
                except json.JSONDecodeError:
                    docker_status["info"] = {"raw": result.stdout}
                    
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Docker状態収集中にエラー: {e}")
                
        return docker_status

    def _collect_process_information(self) -> Dict[str, Any]:
        """プロセス情報を収集"""
        process_info = {}
        
        try:
            # 現在のプロセス情報
            process_info["pid"] = os.getpid()
            process_info["ppid"] = os.getppid() if hasattr(os, 'getppid') else None
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"プロセス情報収集中にエラー: {e}")
                
        return process_info

    def _collect_system_state(self) -> Dict[str, Any]:
        """システム状態を収集"""
        return {
            "system_info": self._collect_detailed_system_info(),
            "docker_status": self._collect_docker_status(),
            "process_info": self._collect_process_information(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _error_report_to_dict(self, report) -> Dict[str, Any]:
        """エラーレポートを辞書に変換"""
        result = {
            "report_id": report.report_id,
            "timestamp": report.timestamp,
            "system_information": report.system_information,
            "environment_variables": report.environment_variables,
            "troubleshooting_guide": report.troubleshooting_guide,
            "next_steps": report.next_steps
        }
        
        if report.hangup_analysis:
            result["hangup_analysis"] = {
                "analysis_id": report.hangup_analysis.analysis_id,
                "issues_count": len(report.hangup_analysis.issues),
                "primary_cause": report.hangup_analysis.primary_cause.title if report.hangup_analysis.primary_cause else None
            }
            
        return result

    def _generate_recovery_suggestions(self, analysis) -> List[str]:
        """復旧提案を生成"""
        suggestions = []
        
        if analysis.primary_cause:
            suggestions.extend(analysis.primary_cause.recommendations)
            
        # 一般的な復旧提案を追加
        suggestions.extend([
            "Docker Desktopまたは Docker Engineを再起動してください",
            "システムリソース（CPU、メモリ、ディスク容量）を確認してください",
            "実行中のコンテナを確認し、不要なものを停止してください"
        ])
        
        return list(set(suggestions))  # 重複を除去

    def _generate_prevention_measures(self, analysis) -> List[str]:
        """予防策を生成"""
        measures = []
        
        # 問題タイプに基づいた予防策
        issue_types = [issue.issue_type for issue in analysis.issues]
        
        if HangupType.PERMISSION_ISSUE in issue_types:
            measures.extend([
                "ユーザーをdockerグループに追加してください",
                "適切なディレクトリ権限を設定してください"
            ])
            
        if HangupType.RESOURCE_EXHAUSTION in issue_types:
            measures.extend([
                "定期的にシステムリソースを監視してください",
                "不要なコンテナやイメージを定期的に削除してください"
            ])
            
        if HangupType.DOCKER_SOCKET_ISSUE in issue_types:
            measures.extend([
                "Docker daemonの自動起動を設定してください",
                "Docker設定を定期的に確認してください"
            ])
            
        # 一般的な予防策
        measures.extend([
            "定期的にDocker system pruneを実行してください",
            "システムの監視とログ確認を習慣化してください"
        ])
        
        return list(set(measures))  # 重複を除去

    def _add_system_info_to_bundle(self, zipf, bundle_id: str, system_info: Dict[str, Any]) -> None:
        """システム情報をバンドルに追加"""
        try:
            content = json.dumps(system_info, ensure_ascii=False, indent=2)
            zipf.writestr(f"{bundle_id}/system_info.json", content)
        except Exception as e:
            if self.logger:
                self.logger.debug(f"システム情報追加中にエラー: {e}")

    def _add_docker_info_to_bundle(self, zipf, bundle_id: str, docker_info: Dict[str, Any]) -> None:
        """Docker情報をバンドルに追加"""
        try:
            content = json.dumps(docker_info, ensure_ascii=False, indent=2)
            zipf.writestr(f"{bundle_id}/docker_info.json", content)
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Docker情報追加中にエラー: {e}")

    def _add_logs_to_bundle(self, zipf, bundle_id: str) -> None:
        """ログファイルをバンドルに追加"""
        try:
            # 簡単なログ情報を追加
            log_content = "Log collection not implemented yet"
            zipf.writestr(f"{bundle_id}/logs.txt", log_content)
        except Exception as e:
            if self.logger:
                self.logger.debug(f"ログ追加中にエラー: {e}")

    def _initialize_detection_patterns(self) -> Dict[str, Any]:
        """検出パターンを初期化"""
        return {
            "docker_socket_patterns": [
                r"permission denied.*docker\.sock",
                r"cannot connect to the docker daemon",
                r"docker daemon.*not running"
            ],
            "timeout_patterns": [
                r"timeout.*expired",
                r"connection.*timed out",
                r"no response.*timeout"
            ],
            "permission_patterns": [
                r"permission denied",
                r"access denied",
                r"insufficient privileges"
            ]
        }

    def _initialize_known_issues_db(self) -> Dict[str, Any]:
        """既知の問題データベースを初期化"""
        return {
            "docker_issues": [
                {
                    "pattern": "docker daemon not running",
                    "solution": "Docker Desktopを起動してください",
                    "severity": "high"
                },
                {
                    "pattern": "permission denied",
                    "solution": "ユーザーをdockerグループに追加してください",
                    "severity": "medium"
                }
            ],
            "timeout_issues": [
                {
                    "pattern": "connection timeout",
                    "solution": "ネットワーク接続を確認してください",
                    "severity": "medium"
                }
            ]
        }
