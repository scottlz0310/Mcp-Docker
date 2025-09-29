"""Run host-installed Bats suites and export JSON summaries."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, List

from services.actions.output import (
    generate_run_id,
    relative_to_output,
    save_json_payload,
    write_log,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATTERN = "tests/test_*.bats"


def _discover_tests(patterns: Iterable[str]) -> List[Path]:
    files: set[Path] = set()
    for pattern in patterns:
        candidate = PROJECT_ROOT / pattern
        if candidate.is_file():
            files.add(candidate)
            continue
        files.update(PROJECT_ROOT.glob(pattern))
    return sorted(files)


def _discover_bats_binary() -> str | None:
    override = os.environ.get("MCP_BATS_BIN")
    if override:
        return override
    return shutil.which("bats")


def _run_single_test(
    test_file: Path,
    *,
    bats_bin: str,
    run_id: str,
) -> dict[str, object]:
    relative = test_file.relative_to(PROJECT_ROOT)
    cmd = [bats_bin, str(relative)]

    start = time.perf_counter()
    completed = subprocess.run(  # noqa: S603 - intentional subprocess call
        cmd,
        check=False,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env={
            **os.environ,
            "PROJECT_ROOT": str(PROJECT_ROOT),
        },
    )
    duration = time.perf_counter() - start

    logs: dict[str, str] = {}
    if completed.stdout:
        stdout_log = write_log(
            completed.stdout,
            run_id=run_id,
            name=relative.stem,
            channel="bats",
        )
        logs["stdout"] = relative_to_output(stdout_log)
    if completed.stderr:
        stderr_log = write_log(
            completed.stderr,
            run_id=run_id,
            name=f"{relative.stem}-err",
            channel="bats",
        )
        logs["stderr"] = relative_to_output(stderr_log)

    return {
        "file": str(relative),
        "status": "passed" if completed.returncode == 0 else "failed",
        "return_code": completed.returncode,
        "duration": round(duration, 3),
        "logs": logs,
    }


def _record_skip(run_id: str, patterns: Iterable[str]) -> None:
    summary_payload: dict[str, object] = {
        "run_id": run_id,
        "success": True,
        "executed": 0,
        "results": [],
        "skipped_patterns": list(patterns),
        "note": "Bats executable not found; suite skipped.",
    }
    summary_path = save_json_payload(
        summary_payload,
        run_id=run_id,
        segments=("quality", "bats"),
    )
    print(
        "⚠️  Bats executable not found. Skipping Bats suite.",
    )
    print(f"ℹ️  Summary saved to {relative_to_output(summary_path)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run host-installed Bats suites and capture summaries.",
    )
    parser.add_argument(
        "patterns",
        nargs="*",
        default=[DEFAULT_PATTERN],
        help="Glob patterns or file paths for Bats tests",
    )
    args = parser.parse_args(argv)

    bats_bin = _discover_bats_binary()
    run_id = generate_run_id()

    if not bats_bin:
        _record_skip(run_id, args.patterns)
        return 0

    tests = _discover_tests(args.patterns)
    if not tests:
        print(
            "No Bats test files were found for the provided patterns.",
            file=sys.stderr,
        )
        return 1

    results: list[dict[str, object]] = [_run_single_test(test, bats_bin=bats_bin, run_id=run_id) for test in tests]
    success = all(item["status"] == "passed" for item in results)

    summary_payload: dict[str, object] = {
        "run_id": run_id,
        "success": success,
        "executed": len(results),
        "results": results,
    }

    summary_path = save_json_payload(
        summary_payload,
        run_id=run_id,
        segments=("quality", "bats"),
    )
    relative_summary = relative_to_output(summary_path)

    status_icon = "✅" if success else "❌"
    print(f"{status_icon} Bats tests completed - summary: {relative_summary}")

    for item in results:
        icon = "✓" if item["status"] == "passed" else "✗"
        print(f"  {icon} {item['file']} ({item['duration']}s)")

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
