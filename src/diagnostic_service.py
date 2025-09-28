#!/usr/bin/env python3
"""
診断サービス - システムヘルスチェックとハングアップ検出

このモジュールはシステムの健全性を監視し、
ハングアップ条件を検出する機能を提供します。
"""

import psutil
import time
import logging
import subprocess
import shutil
import os
from typing import Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
from enum import Enum


class DiagnosticStatus(Enum):
    """診断結果のステータス"""
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class HealthMetrics:
    """システムヘルスメトリクス"""

    cpu_usage: float
    memory_usage: float
    disk_usage: float
    load_average: float
    timestamp: float


@dataclass
class DiagnosticResult:
    """診断結果を表すデータクラス"""
    component: str
    status: DiagnosticStatus
    message: str
    details: Dict[str, Any]
    recommendations: List[str]
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
        self._docker_socket_path = "/var/run/docker.sock"
        self._act_binary_path = None

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

    def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """
        包括的なシステムヘルスチェックを実行

        Returns:
            Dict[str, Any]: 包括的な診断結果
        """
        self.logger.info("包括的なシステムヘルスチェックを開始します...")

        results = []

        # 基本システムヘルスチェック
        basic_health = self.check_system_health()
        results.append(DiagnosticResult(
            component="システムヘルス",
            status=DiagnosticStatus.OK if basic_health.get("status") == "healthy" else DiagnosticStatus.WARNING,
            message=f"CPU: {basic_health.get('cpu_usage', 0):.1f}%, メモリ: {basic_health.get('memory_usage', 0):.1f}%",
            details=basic_health,
            recommendations=[],
            timestamp=time.time()
        ))

        # Docker接続性チェック
        results.append(self.check_docker_connectivity())

        # actバイナリチェック
        results.append(self.check_act_binary())

        # コンテナ権限チェック
        results.append(self.check_container_permissions())

        # ハングアップ条件検出
        hangup_conditions = self.detect_hangup_conditions()
        if hangup_conditions.get("detected", False):
            results.append(DiagnosticResult(
                component="ハングアップ検出",
                status=DiagnosticStatus.WARNING,
                message=f"{len(hangup_conditions.get('conditions', []))}個のハングアップ条件を検出",
                details=hangup_conditions,
                recommendations=["システムリソースの使用量を確認してください"],
                timestamp=time.time()
            ))

        # 全体的なステータスを決定
        error_count = sum(1 for r in results if r.status == DiagnosticStatus.ERROR)
        warning_count = sum(1 for r in results if r.status == DiagnosticStatus.WARNING)

        if error_count > 0:
            overall_status = DiagnosticStatus.ERROR
            summary = f"{error_count}個の重大な問題と{warning_count}個の警告が見つかりました"
        elif warning_count > 0:
            overall_status = DiagnosticStatus.WARNING
            summary = f"{warning_count}個の警告が見つかりました"
        else:
            overall_status = DiagnosticStatus.OK
            summary = "すべてのチェックが正常に完了しました"

        return {
            "overall_status": overall_status.value,
            "summary": summary,
            "results": [
                {
                    "component": r.component,
                    "status": r.status.value,
                    "message": r.message,
                    "details": r.details,
                    "recommendations": r.recommendations,
                    "timestamp": r.timestamp
                }
                for r in results
            ],
            "timestamp": time.time()
        }

    def check_docker_connectivity(self) -> DiagnosticResult:
        """
        Docker接続性をチェック

        Returns:
            DiagnosticResult: Docker接続の診断結果
        """
        self.logger.debug("Docker接続性をチェック中...")

        try:
            # Dockerコマンドの存在確認
            docker_path = shutil.which("docker")
            if not docker_path:
                return DiagnosticResult(
                    component="Docker接続性",
                    status=DiagnosticStatus.ERROR,
                    message="Dockerコマンドが見つかりません",
                    details={"docker_path": None},
                    recommendations=[
                        "Docker Desktopまたは Docker Engineをインストールしてください",
                        "PATHにDockerコマンドが含まれていることを確認してください"
                    ],
                    timestamp=time.time()
                )

            # Dockerバージョン確認
            version_result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if version_result.returncode != 0:
                return DiagnosticResult(
                    component="Docker接続性",
                    status=DiagnosticStatus.ERROR,
                    message="Dockerコマンドの実行に失敗しました",
                    details={"stderr": version_result.stderr, "docker_path": docker_path},
                    recommendations=[
                        "Dockerが正しくインストールされているか確認してください",
                        "Docker Desktopが起動しているか確認してください"
                    ],
                    timestamp=time.time()
                )

            # Docker daemon接続確認
            info_result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=15
            )

            if info_result.returncode != 0:
                return DiagnosticResult(
                    component="Docker接続性",
                    status=DiagnosticStatus.ERROR,
                    message="Docker daemonに接続できません",
                    details={"stderr": info_result.stderr, "docker_version": version_result.stdout.strip()},
                    recommendations=[
                        "Docker Desktopを起動してください",
                        "Docker daemonが実行されているか確認してください",
                        "ユーザーがdockerグループに属しているか確認してください"
                    ],
                    timestamp=time.time()
                )

            # 成功時の詳細情報を取得
            docker_version = version_result.stdout.strip()

            return DiagnosticResult(
                component="Docker接続性",
                status=DiagnosticStatus.OK,
                message="Docker接続は正常です",
                details={"version": docker_version, "docker_path": docker_path},
                recommendations=[],
                timestamp=time.time()
            )

        except subprocess.TimeoutExpired:
            return DiagnosticResult(
                component="Docker接続性",
                status=DiagnosticStatus.ERROR,
                message="Dockerコマンドがタイムアウトしました",
                details={"timeout": True},
                recommendations=[
                    "Docker daemonの応答が遅い可能性があります",
                    "システムリソースを確認してください"
                ],
                timestamp=time.time()
            )
        except Exception as e:
            return DiagnosticResult(
                component="Docker接続性",
                status=DiagnosticStatus.ERROR,
                message=f"予期しないエラーが発生しました: {str(e)}",
                details={"error": str(e)},
                recommendations=["システム管理者に連絡してください"],
                timestamp=time.time()
            )

    def check_act_binary(self) -> DiagnosticResult:
        """
        actバイナリの存在と動作をチェック

        Returns:
            DiagnosticResult: actバイナリの診断結果
        """
        self.logger.debug("actバイナリをチェック中...")

        try:
            # actバイナリの検索
            candidates = [
                shutil.which("act"),
                "/home/linuxbrew/.linuxbrew/bin/act",
                "/usr/local/bin/act",
                "/opt/homebrew/bin/act"
            ]

            act_path = None
            for candidate in candidates:
                if candidate and Path(candidate).exists():
                    act_path = candidate
                    break

            if not act_path:
                return DiagnosticResult(
                    component="actバイナリ",
                    status=DiagnosticStatus.ERROR,
                    message="actバイナリが見つかりません",
                    details={"searched_paths": [c for c in candidates if c]},
                    recommendations=[
                        "以下のコマンドでactをインストールしてください:",
                        "curl -fsSL https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash",
                        "または: brew install act"
                    ],
                    timestamp=time.time()
                )

            # actバージョン確認
            version_result = subprocess.run(
                [act_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if version_result.returncode != 0:
                return DiagnosticResult(
                    component="actバイナリ",
                    status=DiagnosticStatus.ERROR,
                    message="actバイナリの実行に失敗しました",
                    details={"stderr": version_result.stderr, "act_path": act_path},
                    recommendations=[
                        "actバイナリが破損している可能性があります",
                        "actを再インストールしてください"
                    ],
                    timestamp=time.time()
                )

            # actの基本機能テスト（--helpコマンド）
            help_result = subprocess.run(
                [act_path, "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if help_result.returncode != 0:
                return DiagnosticResult(
                    component="actバイナリ",
                    status=DiagnosticStatus.WARNING,
                    message="actのヘルプコマンドが失敗しました",
                    details={"stderr": help_result.stderr, "version": version_result.stdout.strip()},
                    recommendations=["actの設定を確認してください"],
                    timestamp=time.time()
                )

            act_version = version_result.stdout.strip()
            self._act_binary_path = act_path

            return DiagnosticResult(
                component="actバイナリ",
                status=DiagnosticStatus.OK,
                message="actバイナリは正常に動作しています",
                details={"version": act_version, "path": act_path},
                recommendations=[],
                timestamp=time.time()
            )

        except subprocess.TimeoutExpired:
            return DiagnosticResult(
                component="actバイナリ",
                status=DiagnosticStatus.ERROR,
                message="actコマンドがタイムアウトしました",
                details={"timeout": True},
                recommendations=["システムリソースを確認してください"],
                timestamp=time.time()
            )
        except Exception as e:
            return DiagnosticResult(
                component="actバイナリ",
                status=DiagnosticStatus.ERROR,
                message=f"予期しないエラーが発生しました: {str(e)}",
                details={"error": str(e)},
                recommendations=["システム管理者に連絡してください"],
                timestamp=time.time()
            )

    def check_container_permissions(self) -> DiagnosticResult:
        """
        コンテナ権限をチェック

        Returns:
            DiagnosticResult: コンテナ権限の診断結果
        """
        self.logger.debug("コンテナ権限をチェック中...")

        try:
            # 現在のユーザー情報を取得
            user_id = os.getuid() if hasattr(os, "getuid") else None
            group_id = os.getgid() if hasattr(os, "getgid") else None

            details = {
                "user_id": user_id,
                "group_id": group_id,
                "is_root": user_id == 0 if user_id is not None else False
            }

            # Dockerグループの確認
            try:
                groups_result = subprocess.run(
                    ["groups"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if groups_result.returncode == 0:
                    groups = groups_result.stdout.strip().split()
                    details["groups"] = groups
                    details["in_docker_group"] = "docker" in groups
                else:
                    details["groups"] = []
                    details["in_docker_group"] = False
            except Exception:
                details["groups"] = []
                details["in_docker_group"] = False

            # Docker socket権限の確認
            docker_socket = Path(self._docker_socket_path)
            if docker_socket.exists():
                stat_info = docker_socket.stat()
                details["docker_socket_exists"] = True
                details["docker_socket_permissions"] = oct(stat_info.st_mode)[-3:]

                # ソケットへの読み書き権限をテスト
                try:
                    with open(docker_socket, "r"):
                        # ソケットを開けるかテスト（実際には読み込まない）
                        pass
                    details["docker_socket_accessible"] = True
                except PermissionError:
                    details["docker_socket_accessible"] = False
                except Exception:
                    # ソケットファイルなので通常のファイル操作は失敗するが、
                    # 権限があれば別のエラーになる
                    details["docker_socket_accessible"] = True
            else:
                details["docker_socket_exists"] = False
                details["docker_socket_accessible"] = False

            # 権限の問題を判定
            issues = []
            recommendations = []

            if not details.get("docker_socket_exists", False):
                issues.append("Docker socketが見つかりません")
                recommendations.append("Docker daemonが実行されているか確認してください")

            if not details.get("docker_socket_accessible", False):
                issues.append("Docker socketにアクセスできません")
                if not details.get("in_docker_group", False) and not details.get("is_root", False):
                    recommendations.extend([
                        "ユーザーをdockerグループに追加してください: sudo usermod -aG docker $USER",
                        "ログアウト・ログインしてグループ変更を反映してください"
                    ])

            if issues:
                status = DiagnosticStatus.ERROR
                message = "; ".join(issues)
            else:
                status = DiagnosticStatus.OK
                message = "コンテナ権限は正常です"

            return DiagnosticResult(
                component="コンテナ権限",
                status=status,
                message=message,
                details=details,
                recommendations=recommendations,
                timestamp=time.time()
            )

        except Exception as e:
            return DiagnosticResult(
                component="コンテナ権限",
                status=DiagnosticStatus.ERROR,
                message=f"権限チェック中にエラーが発生しました: {str(e)}",
                details={"error": str(e)},
                recommendations=["システム管理者に連絡してください"],
                timestamp=time.time()
            )
