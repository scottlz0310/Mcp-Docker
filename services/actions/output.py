"""Utility helpers for persisting GitHub Actions Simulator artifacts."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from . import ACTIONS_OUTPUT_DIR

_OUTPUT_ENV_VAR = "MCP_ACTIONS_OUTPUT_DIR"


def get_output_root() -> Path:
    """Return the simulator artifact root directory, creating it if needed."""
    env_value = os.environ.get(_OUTPUT_ENV_VAR)
    if env_value:
        root = Path(env_value).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    root = ACTIONS_OUTPUT_DIR
    try:
        root.mkdir(parents=True, exist_ok=True)
        return root
    except PermissionError:
        fallback = Path.home() / ".cache" / "mcp-docker" / "actions"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def ensure_subdir(*segments: Iterable[str] | str) -> Path:
    """Ensure a nested subdirectory exists under the output root."""
    root = get_output_root()
    path = root
    for segment in segments:
        if isinstance(segment, str):
            parts = [segment]
        else:
            parts = list(segment)
        for part in parts:
            if part:
                path = path / part
    path.mkdir(parents=True, exist_ok=True)
    return path


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def generate_run_id() -> str:
    """Generate a unique identifier for a simulator execution."""
    return _timestamp_slug()


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    cleaned = cleaned.strip("-")
    return cleaned or "artifact"


def write_log(
    content: str,
    *,
    run_id: str,
    name: str,
    channel: str,
) -> Path:
    """Persist a log stream and return the written file path."""
    logs_dir = ensure_subdir("logs", channel)
    filename = f"{run_id}-{_slugify(name)}.log"
    path = logs_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def save_json_payload(
    payload: dict[str, Any],
    *,
    run_id: str,
    segments: tuple[str, ...] = ("summaries",),
    filename: str | None = None,
    create_latest: bool = True,
) -> Path:
    """Serialize a payload to JSON under the specified output category."""
    target_dir = ensure_subdir(segments)
    target_dir.mkdir(parents=True, exist_ok=True)
    if filename is None:
        filename = f"{run_id}.json"
    path = target_dir / filename
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if create_latest:
        latest_path = target_dir / "latest.json"
        latest_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return path


def relative_to_output(path: Path) -> str:
    """Return the path relative to the output root when possible."""
    root = get_output_root()
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def list_json_files(*segments: str) -> list[Path]:
    """List stored JSON artifacts inside the given output category."""
    directory = get_output_root().joinpath(*segments)
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob("*.json") if path.name != "latest.json")


def latest_json_path(*segments: str) -> Path | None:
    """Return the latest JSON artifact path for the given category."""
    directory = get_output_root().joinpath(*segments)
    latest = directory / "latest.json"
    if latest.exists():
        return latest
    candidates = list_json_files(*segments)
    return candidates[-1] if candidates else None


def load_summary(path: Path | None = None) -> tuple[Path, dict[str, Any]]:
    """Load a stored simulation summary JSON payload."""
    target = path
    if target is None:
        target = latest_json_path("summaries")
    if target is None or not target.exists():
        raise FileNotFoundError("No simulation summary artifacts were found.")
    data = json.loads(target.read_text(encoding="utf-8"))
    return target, data


__all__ = [
    "generate_run_id",
    "get_output_root",
    "ensure_subdir",
    "write_log",
    "save_json_payload",
    "relative_to_output",
    "list_json_files",
    "latest_json_path",
    "load_summary",
]
