"""Run a lightweight Trivy scan and store results under output/security."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, cast

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECURITY_ROOT = PROJECT_ROOT / "output" / "security"
TRIVY_DIR = SECURITY_ROOT / "trivy"
REPORTS_DIR = TRIVY_DIR / "reports"
SUMMARIES_DIR = TRIVY_DIR / "summaries"
CACHE_DIR = TRIVY_DIR / "cache"
TRIVY_IMAGE = os.environ.get("MCP_TRIVY_IMAGE", "aquasec/trivy:0.54.1")


def _ensure_directories() -> None:
    for path in (
        SECURITY_ROOT,
        TRIVY_DIR,
        REPORTS_DIR,
        SUMMARIES_DIR,
        CACHE_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _ensure_docker() -> None:
    if shutil.which("docker") is None:
        raise RuntimeError(
            "docker command not found. Install Docker to run security scans.",
        )


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _build_image(image: str) -> None:
    subprocess.run(
        ["docker", "build", "-t", image, "."],
        check=True,
    )


def _run_trivy(
    image: str,
    *,
    severity: str,
    fail_on: str | None,
    timeout: str,
) -> tuple[int, str, str]:
    exit_code_flag = "1" if fail_on else "0"
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{CACHE_DIR}:/root/.cache",
        "-v",
        "/var/run/docker.sock:/var/run/docker.sock",
        TRIVY_IMAGE,
        "image",
        "--scanners",
        "vuln",
        "--format",
        "json",
        "--severity",
        severity,
        "--timeout",
        timeout,
        "--ignore-unfixed",
        "--exit-code",
        exit_code_flag,
        image,
    ]

    completed = subprocess.run(  # noqa: S603,S607 - container invocation
        cmd,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode, completed.stdout, completed.stderr


def _collect_vulnerabilities(report: Dict[str, Any]) -> Dict[str, int]:
    breakdown: Dict[str, int] = {}
    raw_results = report.get("Results", [])
    if not isinstance(raw_results, list):
        return breakdown

    raw_results_list = cast(list[Any], raw_results)

    typed_results: list[Dict[str, Any]] = []
    for result_entry in raw_results_list:
        if isinstance(result_entry, dict):
            typed_results.append(cast(Dict[str, Any], result_entry))

    for result_dict in typed_results:
        vulnerabilities = result_dict.get("Vulnerabilities", [])
        if not isinstance(vulnerabilities, list):
            continue
        vulnerability_list = cast(list[Any], vulnerabilities)
        typed_vulns: list[Dict[str, Any]] = []
        for vuln_entry in vulnerability_list:
            if isinstance(vuln_entry, dict):
                typed_vulns.append(cast(Dict[str, Any], vuln_entry))
        for item_dict in typed_vulns:
            severity = str(item_dict.get("Severity", "UNKNOWN")).upper()
            breakdown[severity] = breakdown.get(severity, 0) + 1
    return breakdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a lightweight Trivy security scan.",
    )
    parser.add_argument(
        "--image",
        default="mcp-docker:latest",
        help="Docker image tag to scan",
    )
    parser.add_argument(
        "--severity",
        default="CRITICAL,HIGH",
        help="Comma-separated severities to include (default: CRITICAL,HIGH)",
    )
    parser.add_argument(
        "--fail-on",
        help="Severity threshold that triggers a non-zero exit code",
    )
    parser.add_argument(
        "--timeout",
        default="3m",
        help="Trivy execution timeout (default: 3m)",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip rebuilding the target image before scanning",
    )
    args = parser.parse_args(argv)

    try:
        _ensure_docker()
    except RuntimeError as exc:  # pragma: no cover - defensive
        print(str(exc), file=sys.stderr)
        return 1

    _ensure_directories()

    if not args.skip_build:
        print(f"📦 Building image {args.image} ...")
        start_build = time.perf_counter()
        try:
            _build_image(args.image)
        except subprocess.CalledProcessError as exc:
            # pragma: no cover - defensive
            print(f"❌ Docker build failed: {exc}", file=sys.stderr)
            return 1
        build_duration = time.perf_counter() - start_build
        print(f"✅ Build completed in {build_duration:.1f}s")

    print(f"🔒 Running Trivy scan on {args.image} ...")
    start_scan = time.perf_counter()
    return_code, stdout, stderr = _run_trivy(
        args.image,
        severity=args.severity,
        fail_on=args.fail_on,
        timeout=args.timeout,
    )
    scan_duration = time.perf_counter() - start_scan

    if stderr:
        print(stderr.strip(), file=sys.stderr)

    try:
        report = json.loads(stdout or "{}")
    except json.JSONDecodeError:
        report = {"raw_output": stdout}

    breakdown = _collect_vulnerabilities(report)
    total_findings = sum(breakdown.values())

    run_id = _timestamp()
    report_path = REPORTS_DIR / f"{run_id}-report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary: Dict[str, Any] = {
        "run_id": run_id,
        "image": args.image,
        "severity": args.severity,
        "fail_on": args.fail_on,
        "total_findings": total_findings,
        "breakdown": breakdown,
        "scan_duration_seconds": round(scan_duration, 2),
        "return_code": return_code,
        "report": str(report_path.relative_to(PROJECT_ROOT)),
    }

    summary_path = SUMMARIES_DIR / f"{run_id}-summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    latest_path = SUMMARIES_DIR / "latest.json"
    latest_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if total_findings:
        print(f"⚠️  Found {total_findings} vulnerabilities: {breakdown}")
    else:
        print("✅ No vulnerabilities found for selected severities.")
    print(f"📝 Summary saved to {summary_path.relative_to(PROJECT_ROOT)}")

    if args.fail_on and return_code != 0:
        print(
            "❗ Fail-on severity threshold reached. "
            "Review the report before proceeding.",
            file=sys.stderr,
        )

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
