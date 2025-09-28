#!/usr/bin/env python3
"""
診断サービス - システムヘルスチェックとハングアップ検出

このモジュールはシステムの健全性を監視し、
ハングアップ条件を検出する機能を提供します。
"""

import psutil
import time
import logging
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class HealthMetrics:
    """システムヘルスメトリクス"""

    cpu_usage: float
    memory_usage: float
    disk_usage: float
    load_average: float
    timestamp: float


class DiagnosticService:
    """システム診断サービス"""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.health_history: List[HealthMetrics] = []
        self.hangup_threshold = {
            "cpu_high": 90.0,
            "memory_high": 85.0,
            "response_timeout": 30.0,
        }

    def check_system_health(self) -> Dict[str, Any]:
        """システムヘルスチェックを実行"""
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            load_avg = psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else 0.0

            metrics = HealthMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                load_average=load_avg,
                timestamp=time.time(),
            )

            self.health_history.append(metrics)

            # 履歴を最新100件に制限
            if len(self.health_history) > 100:
                self.health_history = self.health_history[-100:]

            return {
                "cpu_usage": cpu_usage,
                "memory_usage": memory.percent,
                "disk_usage": disk.percent,
                "load_average": load_avg,
                "timestamp": metrics.timestamp,
                "status": "healthy" if self._is_healthy(metrics) else "warning",
            }

        except Exception as e:
            self.logger.error(f"システムヘルスチェックエラー: {e}")
            return {"error": str(e), "status": "error", "timestamp": time.time()}

    def detect_hangup_conditions(self) -> Dict[str, Any]:
        """ハングアップ条件を検出"""
        try:
            conditions = []

            if len(self.health_history) >= 3:
                recent_metrics = self.health_history[-3:]

                # CPU使用率が継続的に高い
                if all(
                    m.cpu_usage > self.hangup_threshold["cpu_high"]
                    for m in recent_metrics
                ):
                    conditions.append(
                        {
                            "type": "high_cpu_usage",
                            "severity": "high",
                            "description": "CPU使用率が継続的に高い状態です",
                        }
                    )

                # メモリ使用率が継続的に高い
                if all(
                    m.memory_usage > self.hangup_threshold["memory_high"]
                    for m in recent_metrics
                ):
                    conditions.append(
                        {
                            "type": "high_memory_usage",
                            "severity": "high",
                            "description": "メモリ使用率が継続的に高い状態です",
                        }
                    )

            return {
                "detected": len(conditions) > 0,
                "conditions": conditions,
                "timestamp": time.time(),
            }

        except Exception as e:
            self.logger.error(f"ハングアップ検出エラー: {e}")
            return {
                "detected": False,
                "conditions": [],
                "error": str(e),
                "timestamp": time.time(),
            }

    def _is_healthy(self, metrics: HealthMetrics) -> bool:
        """メトリクスが健全かどうかを判定"""
        return (
            metrics.cpu_usage < self.hangup_threshold["cpu_high"]
            and metrics.memory_usage < self.hangup_threshold["memory_high"]
        )

    def get_health_history(self) -> List[Dict[str, Any]]:
        """ヘルス履歴を取得"""
        return [
            {
                "cpu_usage": m.cpu_usage,
                "memory_usage": m.memory_usage,
                "disk_usage": m.disk_usage,
                "load_average": m.load_average,
                "timestamp": m.timestamp,
            }
            for m in self.health_history
        ]
