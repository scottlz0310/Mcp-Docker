"""Tests for artifact persistence and summary CLI rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from click.testing import CliRunner

from services.actions import main
from services.actions.output import (
    generate_run_id,
    load_summary,
    relative_to_output,
    save_json_payload,
    write_log,
)


def test_save_and_load_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MCP_ACTIONS_OUTPUT_DIR", str(tmp_path))
    run_id = generate_run_id()
    payload: dict[str, object] = {
        "run_id": run_id,
        "generated_at": "2025-09-27T12:00:00+00:00",
        "results": [],
        "success": True,
        "fail_fast_triggered": False,
        "skipped": [],
        "artifact": "summaries/{run_id}.json".format(run_id=run_id),
    }
    summary_path = save_json_payload(payload, run_id=run_id)

    resolved_path, loaded = load_summary(summary_path)
    assert resolved_path == summary_path
    assert loaded["run_id"] == run_id
    latest_path, _ = load_summary()
    assert latest_path.name == "latest.json"
    latest_path = Path(tmp_path) / "summaries" / "latest.json"
    assert latest_path.exists()


def test_write_log_generates_relative_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MCP_ACTIONS_OUTPUT_DIR", str(tmp_path))
    run_id = "log-run"
    log_path = write_log(
        "example",
        run_id=run_id,
        name="workflow",
        channel="stdout",
    )
    assert log_path.exists()
    assert "logs" in relative_to_output(log_path)


def test_cli_summary_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MCP_ACTIONS_OUTPUT_DIR", str(tmp_path))
    run_id = "cli-run"
    payload: dict[str, object] = {
        "run_id": run_id,
        "generated_at": "2025-09-27T12:34:56+00:00",
        "artifact": f"summaries/{run_id}.json",
        "results": [
            {
                "workflow": ".github/workflows/ci.yml",
                "engine": "act",
                "status": "success",
                "return_code": 0,
                "logs": {"stdout": "logs/stdout/sample.log"},
            }
        ],
        "success": True,
        "fail_fast_triggered": False,
        "skipped": [],
    }
    save_json_payload(payload, run_id=run_id)

    runner = CliRunner()
    result = runner.invoke(main.cli, ["summary"])
    assert result.exit_code == 0
    assert "cli-run" in result.output
    assert "stdout:" in result.output
