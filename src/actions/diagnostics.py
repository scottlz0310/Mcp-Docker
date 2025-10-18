"""軽量診断機能 - services.actions.diagnostic の簡易版"""

import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class DiagnosticResult:
    """診断結果"""

    success: bool
    message: str
    details: Optional[dict] = None


def check_docker() -> DiagnosticResult:
    """Docker存在確認と基本動作チェック"""
    docker_path = shutil.which("docker")
    if not docker_path:
        return DiagnosticResult(success=False, message="Docker not found in PATH", details={"docker_path": None})

    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return DiagnosticResult(
                success=True,
                message="Docker available",
                details={"docker_path": docker_path, "version": result.stdout.strip()},
            )
        else:
            return DiagnosticResult(
                success=False,
                message="Docker command failed",
                details={"docker_path": docker_path, "error": result.stderr},
            )
    except Exception as e:
        return DiagnosticResult(
            success=False, message=f"Docker check failed: {e}", details={"docker_path": docker_path, "error": str(e)}
        )


def check_act() -> DiagnosticResult:
    """act存在確認と基本動作チェック"""
    act_path = shutil.which("act")
    if not act_path:
        return DiagnosticResult(success=False, message="act not found in PATH", details={"act_path": None})

    try:
        result = subprocess.run(["act", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return DiagnosticResult(
                success=True, message="act available", details={"act_path": act_path, "version": result.stdout.strip()}
            )
        else:
            return DiagnosticResult(
                success=False, message="act command failed", details={"act_path": act_path, "error": result.stderr}
            )
    except Exception as e:
        return DiagnosticResult(
            success=False, message=f"act check failed: {e}", details={"act_path": act_path, "error": str(e)}
        )


def run_basic_diagnostics() -> dict[str, DiagnosticResult]:
    """基本診断を実行"""
    return {
        "docker": check_docker(),
        "act": check_act(),
    }


def check_system_health() -> dict:
    """システムヘルスチェック（service.py互換）"""
    diagnostics = run_basic_diagnostics()

    all_success = all(result.success for result in diagnostics.values())

    return {
        "status": "ok" if all_success else "error",
        "checks": {
            name: {"success": result.success, "message": result.message} for name, result in diagnostics.items()
        },
    }
