#!/usr/bin/env python3
"""
パフォーマンス監視と最適化 - ワークフロー実行中のメトリクス収集と分析

このモジュールはワークフロー実行中のパフォーマンスメトリクスを収集し、
ボトルネックと最適化機会を特定する機能を提供します。
"""

import time
import threading
import logging
import psutil
import docker
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import deque
from pathlib import Path
import json
import statistics


@dataclass
class PerformanceMetrics:
    """パフォーマンスメトリクス"""

    timestamp: float
    cpu_percent: float
    memory_rss_mb: float
    memory_vms_mb: float
    memory_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_bytes_sent: float
    network_bytes_recv: float
    docker_operations_count: int = 0
    active_containers: int = 0
    docker_cpu_usage: float = 0.0
    docker_memory_usage_mb: float = 0.0


@dataclass
class ExecutionStage:
    """実行段階のメトリクス"""

    stage_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    peak_cpu: float = 0.0
    peak_memory_mb: float = 0.0
    docker_operations: int = 0
    bottlenecks: List[str] = field(default_factory=list)


@dataclass
class BottleneckAnalysis:
    """ボトルネック分析結果"""

    bottleneck_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    affected_stage: str
    impact_score: float
    recommendations: List[str]
    metrics_evidence: Dict[str, Any]


@dataclass
class OptimizationOpportunity:
    """最適化機会"""

    opportunity_type: str
    priority: str  # LOW, MEDIUM, HIGH
    title: str
    description: str
    estimated_improvement: str
    implementation_effort: str
    recommendations: List[str]


class PerformanceMonitor:
    """パフォーマンス監視クラス"""

    def __init__(self, logger=None, monitoring_interval: float = 0.5):
        self.logger = logger or logging.getLogger(__name__)
        self.monitoring_interval = monitoring_interval
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None

        # メトリクス収集
        self.metrics_history: deque = deque(maxlen=1000)  # 最新1000件を保持
        self.execution_stages: List[ExecutionStage] = []
        self.current_stage: Optional[ExecutionStage] = None

        # Docker監視
        self.docker_client: Optional[docker.DockerClient] = None
        self.docker_operations_count = 0
        self.docker_containers_monitored: Dict[str, Any] = {}

        # ベースライン測定
        self.baseline_metrics: Optional[PerformanceMetrics] = None

        # 分析結果
        self.bottlenecks: List[BottleneckAnalysis] = []
        self.optimization_opportunities: List[OptimizationOpportunity] = []

        # スレッドセーフティ
        self.lock = threading.Lock()

        # 初期化
        self._initialize_docker_client()
        self._measure_baseline()

    def _initialize_docker_client(self):
        """Dockerクライアントを初期化"""
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            self.logger.info("Docker クライアント接続成功")
        except Exception as e:
            self.logger.warning(f"Docker クライアント接続失敗: {e}")
            self.docker_client = None

    def _measure_baseline(self):
        """ベースラインメトリクスを測定"""
        try:
            self.baseline_metrics = self._collect_current_metrics()
            self.logger.info("ベースラインメトリクス測定完了")
        except Exception as e:
            self.logger.error(f"ベースライン測定エラー: {e}")



    def stop_monitoring(self):
        """パフォーマンス監視を停止"""
        with self.lock:
            if not self.monitoring_active:
                return

            self.monitoring_active = False

            # 現在の段階を終了
            if self.current_stage and self.current_stage.end_time is None:
                self.end_stage()

        # スレッドの終了を待機
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=3.0)
            if self.monitor_thread.is_alive():
                self.logger.warning("監視スレッドの終了がタイムアウトしました")

        # 分析を実行
        self._analyze_performance()
        self.logger.info("パフォーマンス監視停止")

    def start_stage(self, stage_name: str):
        """実行段階を開始"""
        with self.lock:
            # 前の段階を終了
            if self.current_stage and self.current_stage.end_time is None:
                self.end_stage()

            # 新しい段階を開始
            self.current_stage = ExecutionStage(
                stage_name=stage_name, start_time=time.time()
            )
            self.execution_stages.append(self.current_stage)

            self.logger.debug(f"実行段階開始: {stage_name}")

    def end_stage(self):
        """現在の実行段階を終了"""
        with self.lock:
            if not self.current_stage or self.current_stage.end_time is not None:
                return

            self.current_stage.end_time = time.time()
            self.current_stage.duration_ms = (
                self.current_stage.end_time - self.current_stage.start_time
            ) * 1000

            # 段階中のピーク値を計算
            stage_metrics = [
                m
                for m in self.metrics_history
                if self.current_stage.start_time
                <= m.timestamp
                <= self.current_stage.end_time
            ]

            if stage_metrics:
                self.current_stage.peak_cpu = max(m.cpu_percent for m in stage_metrics)
                self.current_stage.peak_memory_mb = max(
                    m.memory_rss_mb for m in stage_metrics
                )

            self.logger.debug(
                f"実行段階終了: {self.current_stage.stage_name} "
                f"({self.current_stage.duration_ms:.2f}ms)"
            )

    def record_docker_operation(self, operation_type: str, container_id: str = None):
        """Docker操作を記録"""
        with self.lock:
            self.docker_operations_count += 1

            if self.current_stage:
                self.current_stage.docker_operations += 1

            self.logger.debug(
                f"Docker操作記録: {operation_type} (container: {container_id or 'N/A'})"
            )

    def _collect_current_metrics(self) -> PerformanceMetrics:
        """現在のメトリクスを収集"""
        # システムメトリクス
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()

        # メモリ情報の取得（psutilのバージョンに対応）
        memory_total_mb = memory.total / (1024 * 1024)
        memory_available_mb = memory.available / (1024 * 1024)
        memory_used_mb = memory_total_mb - memory_available_mb
        memory_percent = memory.percent

        # ディスクI/O
        disk_io = psutil.disk_io_counters()
        disk_read_mb = disk_io.read_bytes / (1024 * 1024) if disk_io else 0.0
        disk_write_mb = disk_io.write_bytes / (1024 * 1024) if disk_io else 0.0

        # ネットワークI/O
        net_io = psutil.net_io_counters()
        net_sent = net_io.bytes_sent if net_io else 0.0
        net_recv = net_io.bytes_recv if net_io else 0.0

        # Dockerメトリクス
        docker_cpu_usage = 0.0
        docker_memory_mb = 0.0
        active_containers = 0

        if self.docker_client:
            try:
                containers = self.docker_client.containers.list()
                active_containers = len(containers)

                for container in containers:
                    try:
                        stats = container.stats(stream=False)

                        # CPU使用率計算
                        cpu_delta = (
                            stats["cpu_stats"]["cpu_usage"]["total_usage"]
                            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
                        )
                        system_delta = (
                            stats["cpu_stats"]["system_cpu_usage"]
                            - stats["precpu_stats"]["system_cpu_usage"]
                        )

                        if system_delta > 0:
                            cpu_usage = (
                                (cpu_delta / system_delta)
                                * len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])
                                * 100.0
                            )
                            docker_cpu_usage += cpu_usage

                        # メモリ使用量
                        memory_usage = stats["memory_stats"].get("usage", 0)
                        docker_memory_mb += memory_usage / (1024 * 1024)

                    except Exception as e:
                        self.logger.debug(
                            f"コンテナ統計取得エラー {container.id[:12]}: {e}"
                        )

            except Exception as e:
                self.logger.debug(f"Docker統計取得エラー: {e}")

        return PerformanceMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_rss_mb=memory_used_mb,  # 使用メモリ量を使用
            memory_vms_mb=memory_total_mb,  # 総メモリ量を使用
            memory_percent=memory_percent,
            disk_io_read_mb=disk_read_mb,
            disk_io_write_mb=disk_write_mb,
            network_bytes_sent=net_sent,
            network_bytes_recv=net_recv,
            docker_operations_count=self.docker_operations_count,
            active_containers=active_containers,
            docker_cpu_usage=docker_cpu_usage,
            docker_memory_usage_mb=docker_memory_mb,
        )

    def _monitoring_loop(self):
        """監視ループ（バックグラウンドスレッド）"""
        while self.monitoring_active:
            try:
                metrics = self._collect_current_metrics()

                with self.lock:
                    self.metrics_history.append(metrics)

                time.sleep(self.monitoring_interval)

            except Exception as e:
                self.logger.error(f"メトリクス収集エラー: {e}")
                time.sleep(self.monitoring_interval)

    def _analyze_performance(self):
        """パフォーマンス分析を実行"""
        try:
            self._detect_bottlenecks()
            self._identify_optimization_opportunities()
            self.logger.info("パフォーマンス分析完了")
        except Exception as e:
            self.logger.error(f"パフォーマンス分析エラー: {e}")

    def _detect_bottlenecks(self):
        """ボトルネックを検出"""
        if not self.metrics_history:
            return

        metrics_list = list(self.metrics_history)

        # CPU ボトルネック検出
        cpu_values = [m.cpu_percent for m in metrics_list]
        avg_cpu = statistics.mean(cpu_values)
        max_cpu = max(cpu_values)

        if avg_cpu > 80:
            self.bottlenecks.append(
                BottleneckAnalysis(
                    bottleneck_type="CPU_HIGH_USAGE",
                    severity="HIGH" if avg_cpu > 90 else "MEDIUM",
                    description=f"CPU使用率が継続的に高い状態です (平均: {avg_cpu:.1f}%)",
                    affected_stage="全体",
                    impact_score=avg_cpu / 100.0,
                    recommendations=[
                        "並列処理の最適化を検討してください",
                        "CPU集約的なタスクの分散を検討してください",
                        "不要なプロセスの停止を検討してください",
                    ],
                    metrics_evidence={"avg_cpu": avg_cpu, "max_cpu": max_cpu},
                )
            )

        # メモリ ボトルネック検出
        memory_values = [m.memory_percent for m in metrics_list]
        avg_memory = statistics.mean(memory_values)
        max_memory = max(memory_values)

        if avg_memory > 85:
            self.bottlenecks.append(
                BottleneckAnalysis(
                    bottleneck_type="MEMORY_HIGH_USAGE",
                    severity="CRITICAL" if avg_memory > 95 else "HIGH",
                    description=f"メモリ使用率が継続的に高い状態です (平均: {avg_memory:.1f}%)",
                    affected_stage="全体",
                    impact_score=avg_memory / 100.0,
                    recommendations=[
                        "メモリリークの確認を行ってください",
                        "不要なデータの解放を検討してください",
                        "メモリ効率的なアルゴリズムの採用を検討してください",
                    ],
                    metrics_evidence={
                        "avg_memory": avg_memory,
                        "max_memory": max_memory,
                    },
                )
            )

        # Docker ボトルネック検出
        docker_cpu_values = [
            m.docker_cpu_usage for m in metrics_list if m.docker_cpu_usage > 0
        ]
        if docker_cpu_values:
            avg_docker_cpu = statistics.mean(docker_cpu_values)
            if avg_docker_cpu > 70:
                self.bottlenecks.append(
                    BottleneckAnalysis(
                        bottleneck_type="DOCKER_CPU_HIGH",
                        severity="MEDIUM",
                        description=f"Dockerコンテナの CPU使用率が高い状態です (平均: {avg_docker_cpu:.1f}%)",
                        affected_stage="Docker操作",
                        impact_score=avg_docker_cpu / 100.0,
                        recommendations=[
                            "コンテナのリソース制限を見直してください",
                            "コンテナイメージの最適化を検討してください",
                            "不要なコンテナの停止を検討してください",
                        ],
                        metrics_evidence={"avg_docker_cpu": avg_docker_cpu},
                    )
                )

        # 実行段階別ボトルネック検出
        for stage in self.execution_stages:
            if stage.duration_ms and stage.duration_ms > 30000:  # 30秒以上
                severity = "HIGH" if stage.duration_ms > 120000 else "MEDIUM"  # 2分以上は高重要度
                self.bottlenecks.append(
                    BottleneckAnalysis(
                        bottleneck_type="STAGE_SLOW_EXECUTION",
                        severity=severity,
                        description=f"実行段階 '{stage.stage_name}' の実行時間が長すぎます ({stage.duration_ms / 1000:.1f}秒)",
                        affected_stage=stage.stage_name,
                        impact_score=min(
                            stage.duration_ms / 60000, 1.0
                        ),  # 1分を最大とする
                        recommendations=[
                            "この段階の処理を並列化できないか検討してください",
                            "不要な処理が含まれていないか確認してください",
                            "外部依存の最適化を検討してください",
                            "タイムアウト設定の見直しを検討してください",
                        ],
                        metrics_evidence={
                            "duration_ms": stage.duration_ms,
                            "peak_cpu": stage.peak_cpu,
                            "peak_memory_mb": stage.peak_memory_mb,
                            "docker_operations": stage.docker_operations,
                        },
                    )
                )

        # I/O ボトルネック検出
        disk_read_values = [m.disk_io_read_mb for m in metrics_list]
        # disk_write_values = [m.disk_io_write_mb for m in metrics_list]  # 将来の使用のため保留

        if len(disk_read_values) > 1:
            disk_read_rate = (max(disk_read_values) - min(disk_read_values)) / (
                (metrics_list[-1].timestamp - metrics_list[0].timestamp) / 60
            )  # MB/分

            if disk_read_rate > 1000:  # 1GB/分以上の読み込み
                self.bottlenecks.append(
                    BottleneckAnalysis(
                        bottleneck_type="HIGH_DISK_IO_READ",
                        severity="MEDIUM",
                        description=f"ディスク読み込み速度が高い状態です ({disk_read_rate:.1f}MB/分)",
                        affected_stage="全体",
                        impact_score=min(disk_read_rate / 2000, 1.0),
                        recommendations=[
                            "ディスクI/Oの最適化を検討してください",
                            "SSDの使用を検討してください",
                            "ファイルアクセスパターンの改善を検討してください",
                        ],
                        metrics_evidence={"disk_read_rate_mb_per_min": disk_read_rate},
                    )
                )

        # ネットワーク ボトルネック検出
        network_sent_values = [m.network_bytes_sent for m in metrics_list]
        # network_recv_values = [m.network_bytes_recv for m in metrics_list]  # 将来の使用のため保留

        if len(network_sent_values) > 1:
            network_sent_rate = (max(network_sent_values) - min(network_sent_values)) / (
                (metrics_list[-1].timestamp - metrics_list[0].timestamp) / 60
            )  # bytes/分

            if network_sent_rate > 100 * 1024 * 1024:  # 100MB/分以上の送信
                self.bottlenecks.append(
                    BottleneckAnalysis(
                        bottleneck_type="HIGH_NETWORK_USAGE",
                        severity="MEDIUM",
                        description=f"ネットワーク使用量が高い状態です ({network_sent_rate / (1024*1024):.1f}MB/分)",
                        affected_stage="全体",
                        impact_score=min(network_sent_rate / (200 * 1024 * 1024), 1.0),
                        recommendations=[
                            "ネットワーク通信の最適化を検討してください",
                            "データ圧縮の使用を検討してください",
                            "不要な通信の削減を検討してください",
                        ],
                        metrics_evidence={"network_sent_rate_mb_per_min": network_sent_rate / (1024*1024)},
                    )
                )

        # リソース変動ボトルネック検出
        if len(cpu_values) > 10:
            cpu_volatility = statistics.stdev(cpu_values)
            if cpu_volatility > 20:  # CPU使用率の標準偏差が20%以上
                self.bottlenecks.append(
                    BottleneckAnalysis(
                        bottleneck_type="CPU_USAGE_VOLATILITY",
                        severity="MEDIUM",
                        description=f"CPU使用率の変動が激しい状態です (標準偏差: {cpu_volatility:.1f}%)",
                        affected_stage="全体",
                        impact_score=min(cpu_volatility / 40, 1.0),
                        recommendations=[
                            "処理負荷の平準化を検討してください",
                            "バッチ処理の最適化を検討してください",
                            "リソース制限の設定を検討してください",
                        ],
                        metrics_evidence={"cpu_volatility": cpu_volatility, "cpu_average": avg_cpu},
                    )
                )

    def _identify_optimization_opportunities(self):
        """最適化機会を特定"""
        if not self.metrics_history:
            return

        metrics_list = list(self.metrics_history)

        # Docker操作の最適化機会
        total_docker_ops = self.docker_operations_count
        if total_docker_ops > 50:
            self.optimization_opportunities.append(
                OptimizationOpportunity(
                    opportunity_type="DOCKER_OPERATIONS_OPTIMIZATION",
                    priority="MEDIUM",
                    title="Docker操作の最適化",
                    description=f"Docker操作が多数実行されています ({total_docker_ops}回)",
                    estimated_improvement="実行時間 10-30% 短縮",
                    implementation_effort="中程度",
                    recommendations=[
                        "Docker操作のバッチ化を検討してください",
                        "不要なコンテナの作成/削除を削減してください",
                        "Dockerイメージのキャッシュ戦略を最適化してください",
                    ],
                )
            )

        # メモリ使用量の最適化機会
        memory_values = [m.memory_rss_mb for m in metrics_list]
        if memory_values:
            peak_memory = max(memory_values)
            if (
                self.baseline_metrics
                and peak_memory > self.baseline_metrics.memory_rss_mb * 3
            ):
                self.optimization_opportunities.append(
                    OptimizationOpportunity(
                        opportunity_type="MEMORY_USAGE_OPTIMIZATION",
                        priority="HIGH",
                        title="メモリ使用量の最適化",
                        description=f"ピークメモリ使用量がベースラインの3倍を超えています ({peak_memory:.1f}MB)",
                        estimated_improvement="メモリ使用量 20-50% 削減",
                        implementation_effort="高",
                        recommendations=[
                            "メモリプロファイリングを実行してください",
                            "大きなオブジェクトの適切な解放を確認してください",
                            "ストリーミング処理の採用を検討してください",
                        ],
                    )
                )

        # 実行時間の最適化機会
        long_stages = [
            s for s in self.execution_stages if s.duration_ms and s.duration_ms > 10000
        ]
        if len(long_stages) > 2:
            total_long_stage_time = sum(s.duration_ms for s in long_stages)
            self.optimization_opportunities.append(
                OptimizationOpportunity(
                    opportunity_type="EXECUTION_TIME_OPTIMIZATION",
                    priority="HIGH",
                    title="実行時間の最適化",
                    description=f"長時間実行される段階が複数あります ({len(long_stages)}個, 合計{total_long_stage_time/1000:.1f}秒)",
                    estimated_improvement="全体実行時間 15-40% 短縮",
                    implementation_effort="中程度",
                    recommendations=[
                        "並列実行可能な処理を特定してください",
                        "I/O待機時間の最適化を検討してください",
                        "キャッシュ戦略の導入を検討してください",
                        "段階間の依存関係を見直してください",
                    ],
                )
            )

        # リソース効率の最適化機会
        cpu_values = [m.cpu_percent for m in metrics_list]
        if cpu_values and memory_values:
            avg_cpu = statistics.mean(cpu_values)
            avg_memory = statistics.mean(memory_values)

            # 低リソース使用率の場合
            if avg_cpu < 30 and avg_memory < 50:
                self.optimization_opportunities.append(
                    OptimizationOpportunity(
                        opportunity_type="RESOURCE_UNDERUTILIZATION",
                        priority="MEDIUM",
                        title="リソース使用率の最適化",
                        description=f"CPU ({avg_cpu:.1f}%) とメモリ ({avg_memory:.1f}%) の使用率が低い状態です",
                        estimated_improvement="処理速度 20-50% 向上",
                        implementation_effort="低",
                        recommendations=[
                            "並列処理数の増加を検討してください",
                            "バッチサイズの増加を検討してください",
                            "より高性能なアルゴリズムの採用を検討してください",
                        ],
                    )
                )

        # Docker最適化機会の詳細化
        if self.execution_stages:
            docker_heavy_stages = [
                s for s in self.execution_stages
                if s.docker_operations > 10 and s.duration_ms and s.duration_ms > 5000
            ]

            if docker_heavy_stages:
                self.optimization_opportunities.append(
                    OptimizationOpportunity(
                        opportunity_type="DOCKER_STAGE_OPTIMIZATION",
                        priority="HIGH",
                        title="Docker集約段階の最適化",
                        description=f"Docker操作が集中している段階があります ({len(docker_heavy_stages)}個)",
                        estimated_improvement="Docker関連処理 30-60% 短縮",
                        implementation_effort="中程度",
                        recommendations=[
                            "Docker操作の事前準備を検討してください",
                            "コンテナの再利用戦略を検討してください",
                            "Docker Buildkitの活用を検討してください",
                            "イメージレイヤーキャッシュの最適化を検討してください",
                        ],
                    )
                )

        # 段階間最適化機会
        if len(self.execution_stages) > 3:
            # 段階間の待機時間を分析
            stage_gaps = []
            for i in range(len(self.execution_stages) - 1):
                current_stage = self.execution_stages[i]
                next_stage = self.execution_stages[i + 1]

                if (current_stage.end_time and next_stage.start_time and
                    next_stage.start_time > current_stage.end_time):
                    gap_ms = (next_stage.start_time - current_stage.end_time) * 1000
                    if gap_ms > 1000:  # 1秒以上のギャップ
                        stage_gaps.append(gap_ms)

            if stage_gaps and statistics.mean(stage_gaps) > 2000:  # 平均2秒以上のギャップ
                total_gap_time = sum(stage_gaps) / 1000
                self.optimization_opportunities.append(
                    OptimizationOpportunity(
                        opportunity_type="STAGE_TRANSITION_OPTIMIZATION",
                        priority="MEDIUM",
                        title="段階間遷移の最適化",
                        description=f"段階間に待機時間があります (合計{total_gap_time:.1f}秒)",
                        estimated_improvement="全体実行時間 5-15% 短縮",
                        implementation_effort="低",
                        recommendations=[
                            "段階間の準備処理を並列化してください",
                            "リソースの事前確保を検討してください",
                            "段階間のデータ受け渡しを最適化してください",
                        ],
                    )
                )

        # ワークフロー特有の最適化機会
        workflow_stages = [s for s in self.execution_stages if "workflow" in s.stage_name.lower()]
        if len(workflow_stages) > 1:
            workflow_total_time = sum(s.duration_ms for s in workflow_stages if s.duration_ms)
            if workflow_total_time > 60000:  # 1分以上のワークフロー処理
                self.optimization_opportunities.append(
                    OptimizationOpportunity(
                        opportunity_type="WORKFLOW_EXECUTION_OPTIMIZATION",
                        priority="HIGH",
                        title="ワークフロー実行の最適化",
                        description=f"ワークフロー実行時間が長い状態です ({workflow_total_time/1000:.1f}秒)",
                        estimated_improvement="ワークフロー実行時間 25-50% 短縮",
                        implementation_effort="高",
                        recommendations=[
                            "ワークフロージョブの並列化を検討してください",
                            "不要なステップの削除を検討してください",
                            "キャッシュ戦略の改善を検討してください",
                            "act実行オプションの最適化を検討してください",
                        ],
                    )
                )

    def get_performance_summary(self) -> Dict[str, Any]:
        """パフォーマンスサマリーを取得"""
        if not self.metrics_history:
            return {"error": "メトリクスデータがありません"}

        metrics_list = list(self.metrics_history)

        # 基本統計
        cpu_values = [m.cpu_percent for m in metrics_list]
        memory_values = [m.memory_rss_mb for m in metrics_list]

        total_duration = 0
        if self.execution_stages:
            completed_stages = [
                s for s in self.execution_stages if s.duration_ms is not None
            ]
            total_duration = sum(s.duration_ms for s in completed_stages)

        return {
            "monitoring_duration_seconds": (
                metrics_list[-1].timestamp - metrics_list[0].timestamp
                if len(metrics_list) > 1
                else 0
            ),
            "total_execution_time_ms": total_duration,
            "metrics_collected": len(metrics_list),
            "cpu_usage": {
                "average": statistics.mean(cpu_values) if cpu_values else 0,
                "peak": max(cpu_values) if cpu_values else 0,
                "minimum": min(cpu_values) if cpu_values else 0,
            },
            "memory_usage": {
                "average_mb": statistics.mean(memory_values) if memory_values else 0,
                "peak_mb": max(memory_values) if memory_values else 0,
                "minimum_mb": min(memory_values) if memory_values else 0,
            },
            "docker_operations": {
                "total_count": self.docker_operations_count,
                "operations_per_minute": (
                    self.docker_operations_count
                    / ((metrics_list[-1].timestamp - metrics_list[0].timestamp) / 60)
                    if len(metrics_list) > 1
                    else 0
                ),
            },
            "execution_stages": len(self.execution_stages),
            "bottlenecks_detected": len(self.bottlenecks),
            "optimization_opportunities": len(self.optimization_opportunities),
        }

    def get_detailed_analysis(self) -> Dict[str, Any]:
        """詳細分析結果を取得"""
        return {
            "performance_summary": self.get_performance_summary(),
            "bottlenecks": [
                {
                    "type": b.bottleneck_type,
                    "severity": b.severity,
                    "description": b.description,
                    "affected_stage": b.affected_stage,
                    "impact_score": b.impact_score,
                    "recommendations": b.recommendations,
                    "evidence": b.metrics_evidence,
                }
                for b in self.bottlenecks
            ],
            "optimization_opportunities": [
                {
                    "type": o.opportunity_type,
                    "priority": o.priority,
                    "title": o.title,
                    "description": o.description,
                    "estimated_improvement": o.estimated_improvement,
                    "implementation_effort": o.implementation_effort,
                    "recommendations": o.recommendations,
                }
                for o in self.optimization_opportunities
            ],
            "execution_stages": [
                {
                    "stage_name": s.stage_name,
                    "duration_ms": s.duration_ms,
                    "peak_cpu": s.peak_cpu,
                    "peak_memory_mb": s.peak_memory_mb,
                    "docker_operations": s.docker_operations,
                    "bottlenecks": s.bottlenecks,
                }
                for s in self.execution_stages
                if s.duration_ms is not None
            ],
        }

    def export_metrics(self, output_path: Path, format: str = "json") -> bool:
        """メトリクスをファイルにエクスポート"""
        try:
            if format.lower() == "json":
                export_data = {
                    "metadata": {
                        "export_timestamp": time.time(),
                        "monitoring_interval": self.monitoring_interval,
                        "total_metrics": len(self.metrics_history),
                    },
                    "analysis": self.get_detailed_analysis(),
                    "raw_metrics": [
                        {
                            "timestamp": m.timestamp,
                            "cpu_percent": m.cpu_percent,
                            "memory_rss_mb": m.memory_rss_mb,
                            "memory_percent": m.memory_percent,
                            "docker_operations_count": m.docker_operations_count,
                            "active_containers": m.active_containers,
                            "docker_cpu_usage": m.docker_cpu_usage,
                            "docker_memory_usage_mb": m.docker_memory_usage_mb,
                        }
                        for m in list(self.metrics_history)
                    ],
                }

                output_path.write_text(
                    json.dumps(export_data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                self.logger.info(
                    f"パフォーマンスメトリクスを {output_path} にエクスポートしました"
                )
                return True

            else:
                self.logger.error(f"サポートされていない形式: {format}")
                return False

        except Exception as e:
            self.logger.error(f"メトリクスエクスポートエラー: {e}")
            return False

    def is_monitoring(self) -> bool:
        """監視中かどうかを確認"""
        return self.monitoring_active

    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """現在のメトリクスを取得"""
        try:
            return self._collect_current_metrics()
        except Exception as e:
            self.logger.error(f"現在のメトリクス取得エラー: {e}")
            return None

    def get_summary_metrics(self) -> Dict[str, Any]:
        """サマリーメトリクスを取得（SimulationServiceとの互換性のため）"""
        return self.get_performance_summary()

    def analyze_bottlenecks(self) -> List[BottleneckAnalysis]:
        """ボトルネック分析を実行して結果を返す"""
        if not self.bottlenecks:
            self._detect_bottlenecks()
        return self.bottlenecks

    def identify_optimization_opportunities(self) -> List[OptimizationOpportunity]:
        """最適化機会を特定して結果を返す"""
        if not self.optimization_opportunities:
            self._identify_optimization_opportunities()
        return self.optimization_opportunities

    def start_monitoring(self, stage_name: str = None):
        """パフォーマンス監視を開始（オプションで初期段階名を指定）"""
        with self.lock:
            if self.monitoring_active:
                self.logger.warning("パフォーマンス監視は既に開始されています")
                return

            self.monitoring_active = True
            self.metrics_history.clear()
            self.execution_stages.clear()
            self.current_stage = None
            self.docker_operations_count = 0
            self.bottlenecks.clear()
            self.optimization_opportunities.clear()

            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop, daemon=True, name="PerformanceMonitor"
            )
            self.monitor_thread.start()

            # 初期段階を開始（指定された場合）
            if stage_name:
                self.start_stage(stage_name)

            self.logger.info("パフォーマンス監視開始")

    def record_workflow_stage(self, stage_name: str, stage_type: str = "workflow"):
        """ワークフロー段階を記録（より詳細な段階管理）"""
        with self.lock:
            if self.current_stage and self.current_stage.end_time is None:
                self.end_stage()

            # 新しい段階を開始
            self.current_stage = ExecutionStage(
                stage_name=f"{stage_type}:{stage_name}",
                start_time=time.time()
            )
            self.execution_stages.append(self.current_stage)

            self.logger.debug(f"ワークフロー段階開始: {stage_type}:{stage_name}")

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """リアルタイムメトリクスを取得"""
        current_metrics = self.get_current_metrics()
        if not current_metrics:
            return {"error": "メトリクス取得に失敗しました"}

        # 最近のメトリクス履歴から傾向を分析
        recent_metrics = list(self.metrics_history)[-10:] if len(self.metrics_history) >= 10 else list(self.metrics_history)

        trends = {}
        if len(recent_metrics) >= 2:
            # CPU使用率の傾向
            cpu_values = [m.cpu_percent for m in recent_metrics]
            cpu_trend = "increasing" if cpu_values[-1] > cpu_values[0] else "decreasing" if cpu_values[-1] < cpu_values[0] else "stable"

            # メモリ使用率の傾向
            memory_values = [m.memory_percent for m in recent_metrics]
            memory_trend = "increasing" if memory_values[-1] > memory_values[0] else "decreasing" if memory_values[-1] < memory_values[0] else "stable"

            trends = {
                "cpu_trend": cpu_trend,
                "memory_trend": memory_trend,
                "cpu_change_percent": cpu_values[-1] - cpu_values[0] if len(cpu_values) >= 2 else 0,
                "memory_change_percent": memory_values[-1] - memory_values[0] if len(memory_values) >= 2 else 0,
            }

        return {
            "current_metrics": {
                "timestamp": current_metrics.timestamp,
                "cpu_percent": current_metrics.cpu_percent,
                "memory_percent": current_metrics.memory_percent,
                "memory_rss_mb": current_metrics.memory_rss_mb,
                "docker_operations_count": current_metrics.docker_operations_count,
                "active_containers": current_metrics.active_containers,
                "docker_cpu_usage": current_metrics.docker_cpu_usage,
                "docker_memory_usage_mb": current_metrics.docker_memory_usage_mb,
            },
            "trends": trends,
            "monitoring_status": {
                "is_active": self.monitoring_active,
                "metrics_collected": len(self.metrics_history),
                "current_stage": self.current_stage.stage_name if self.current_stage else None,
                "total_stages": len(self.execution_stages),
            }
        }

    def detect_performance_issues(self) -> List[Dict[str, Any]]:
        """パフォーマンス問題をリアルタイムで検出"""
        issues = []
        current_metrics = self.get_current_metrics()

        if not current_metrics:
            return [{"type": "METRICS_UNAVAILABLE", "severity": "ERROR", "message": "メトリクス取得に失敗しました"}]

        # 高CPU使用率の検出
        if current_metrics.cpu_percent > 90:
            issues.append({
                "type": "HIGH_CPU_USAGE",
                "severity": "CRITICAL" if current_metrics.cpu_percent > 95 else "HIGH",
                "message": f"CPU使用率が非常に高い状態です ({current_metrics.cpu_percent:.1f}%)",
                "value": current_metrics.cpu_percent,
                "threshold": 90,
                "recommendations": [
                    "CPU集約的なタスクの最適化を検討してください",
                    "並列処理の見直しを行ってください"
                ]
            })

        # 高メモリ使用率の検出
        if current_metrics.memory_percent > 85:
            issues.append({
                "type": "HIGH_MEMORY_USAGE",
                "severity": "CRITICAL" if current_metrics.memory_percent > 95 else "HIGH",
                "message": f"メモリ使用率が非常に高い状態です ({current_metrics.memory_percent:.1f}%)",
                "value": current_metrics.memory_percent,
                "threshold": 85,
                "recommendations": [
                    "メモリリークの確認を行ってください",
                    "不要なデータの解放を検討してください"
                ]
            })

        # Docker関連の問題検出
        if current_metrics.docker_cpu_usage > 80:
            issues.append({
                "type": "HIGH_DOCKER_CPU",
                "severity": "MEDIUM",
                "message": f"Dockerコンテナの CPU使用率が高い状態です ({current_metrics.docker_cpu_usage:.1f}%)",
                "value": current_metrics.docker_cpu_usage,
                "threshold": 80,
                "recommendations": [
                    "コンテナのリソース制限を見直してください",
                    "不要なコンテナの停止を検討してください"
                ]
            })

        # 長時間実行段階の検出
        if self.current_stage and self.current_stage.start_time:
            stage_duration = time.time() - self.current_stage.start_time
            if stage_duration > 60:  # 60秒以上
                issues.append({
                    "type": "LONG_RUNNING_STAGE",
                    "severity": "MEDIUM",
                    "message": f"実行段階 '{self.current_stage.stage_name}' が長時間実行されています ({stage_duration:.1f}秒)",
                    "value": stage_duration,
                    "threshold": 60,
                    "stage_name": self.current_stage.stage_name,
                    "recommendations": [
                        "この段階の処理内容を確認してください",
                        "ハングアップの可能性を調査してください"
                    ]
                })

        return issues

    def generate_performance_report(self) -> Dict[str, Any]:
        """包括的なパフォーマンスレポートを生成"""
        if not self.metrics_history:
            return {"error": "メトリクスデータが不足しています"}

        # 基本統計の計算
        metrics_list = list(self.metrics_history)

        # CPU統計
        cpu_values = [m.cpu_percent for m in metrics_list]
        cpu_stats = {
            "average": statistics.mean(cpu_values) if cpu_values else 0,
            "peak": max(cpu_values) if cpu_values else 0,
            "minimum": min(cpu_values) if cpu_values else 0,
            "median": statistics.median(cpu_values) if cpu_values else 0,
            "std_dev": statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0,
        }

        # メモリ統計
        memory_values = [m.memory_percent for m in metrics_list]
        memory_stats = {
            "average": statistics.mean(memory_values) if memory_values else 0,
            "peak": max(memory_values) if memory_values else 0,
            "minimum": min(memory_values) if memory_values else 0,
            "median": statistics.median(memory_values) if memory_values else 0,
            "std_dev": statistics.stdev(memory_values) if len(memory_values) > 1 else 0,
        }

        # Docker統計
        docker_ops_values = [m.docker_operations_count for m in metrics_list]
        docker_stats = {
            "total_operations": max(docker_ops_values) if docker_ops_values else 0,
            "operations_per_minute": (
                max(docker_ops_values) / ((metrics_list[-1].timestamp - metrics_list[0].timestamp) / 60)
                if len(metrics_list) > 1 and docker_ops_values else 0
            ),
            "peak_containers": max(m.active_containers for m in metrics_list),
        }

        # 段階別分析
        stage_analysis = []
        for stage in self.execution_stages:
            if stage.duration_ms is not None:
                stage_metrics = [
                    m for m in metrics_list
                    if stage.start_time <= m.timestamp <= (stage.end_time or time.time())
                ]

                stage_info = {
                    "stage_name": stage.stage_name,
                    "duration_ms": stage.duration_ms,
                    "duration_seconds": stage.duration_ms / 1000,
                    "peak_cpu": stage.peak_cpu,
                    "peak_memory_mb": stage.peak_memory_mb,
                    "docker_operations": stage.docker_operations,
                    "metrics_count": len(stage_metrics),
                }

                if stage_metrics:
                    stage_cpu_avg = statistics.mean(m.cpu_percent for m in stage_metrics)
                    stage_memory_avg = statistics.mean(m.memory_percent for m in stage_metrics)
                    stage_info.update({
                        "average_cpu": stage_cpu_avg,
                        "average_memory": stage_memory_avg,
                    })

                stage_analysis.append(stage_info)

        # パフォーマンス評価
        performance_score = self._calculate_performance_score(cpu_stats, memory_stats, docker_stats)

        return {
            "report_metadata": {
                "generated_at": time.time(),
                "monitoring_duration_seconds": (
                    metrics_list[-1].timestamp - metrics_list[0].timestamp
                    if len(metrics_list) > 1 else 0
                ),
                "total_metrics_collected": len(metrics_list),
                "performance_score": performance_score,
            },
            "system_performance": {
                "cpu_statistics": cpu_stats,
                "memory_statistics": memory_stats,
                "docker_statistics": docker_stats,
            },
            "execution_analysis": {
                "total_stages": len(self.execution_stages),
                "completed_stages": len([s for s in self.execution_stages if s.duration_ms is not None]),
                "stage_details": stage_analysis,
            },
            "bottlenecks": [
                {
                    "type": b.bottleneck_type,
                    "severity": b.severity,
                    "description": b.description,
                    "affected_stage": b.affected_stage,
                    "impact_score": b.impact_score,
                    "recommendations": b.recommendations,
                }
                for b in self.bottlenecks
            ],
            "optimization_opportunities": [
                {
                    "type": o.opportunity_type,
                    "priority": o.priority,
                    "title": o.title,
                    "description": o.description,
                    "estimated_improvement": o.estimated_improvement,
                    "implementation_effort": o.implementation_effort,
                    "recommendations": o.recommendations,
                }
                for o in self.optimization_opportunities
            ],
            "recommendations": self._generate_overall_recommendations(cpu_stats, memory_stats, docker_stats),
        }

    def _calculate_performance_score(self, cpu_stats: Dict, memory_stats: Dict, docker_stats: Dict) -> float:
        """パフォーマンススコアを計算（0-100）"""
        # CPU スコア（低い使用率ほど高スコア）
        cpu_score = max(0, 100 - cpu_stats["average"])

        # メモリ スコア（低い使用率ほど高スコア）
        memory_score = max(0, 100 - memory_stats["average"])

        # Docker効率スコア（操作数が適度で、コンテナ数が少ないほど高スコア）
        docker_score = 100
        if docker_stats["operations_per_minute"] > 10:
            docker_score -= min(50, (docker_stats["operations_per_minute"] - 10) * 2)
        if docker_stats["peak_containers"] > 5:
            docker_score -= min(30, (docker_stats["peak_containers"] - 5) * 5)

        # 重み付き平均
        overall_score = (cpu_score * 0.4 + memory_score * 0.4 + docker_score * 0.2)
        return round(max(0, min(100, overall_score)), 2)

    def _generate_overall_recommendations(self, cpu_stats: Dict, memory_stats: Dict, docker_stats: Dict) -> List[str]:
        """全体的な推奨事項を生成"""
        recommendations = []

        if cpu_stats["average"] > 70:
            recommendations.append("CPU使用率が高いため、並列処理の最適化や処理の分散を検討してください")

        if memory_stats["average"] > 80:
            recommendations.append("メモリ使用率が高いため、メモリリークの確認や効率的なデータ構造の使用を検討してください")

        if docker_stats["operations_per_minute"] > 15:
            recommendations.append("Docker操作が頻繁に実行されているため、操作のバッチ化やキャッシュ戦略の改善を検討してください")

        if docker_stats["peak_containers"] > 10:
            recommendations.append("同時実行コンテナ数が多いため、リソース制限の設定や不要なコンテナの削除を検討してください")

        # 段階別の推奨事項
        long_stages = [s for s in self.execution_stages if s.duration_ms and s.duration_ms > 30000]
        if len(long_stages) > 2:
            recommendations.append("長時間実行される段階が複数あるため、処理の最適化やタイムアウト設定の見直しを検討してください")

        if not recommendations:
            recommendations.append("パフォーマンスは良好です。現在の設定を維持してください")

        return recommendations
