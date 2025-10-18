"""Utility helpers for resolving project and workflow paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT_MARKERS: tuple[str, ...] = (".git", "pyproject.toml", "uv.lock")


def find_project_root(start: Path | None = None, markers: Iterable[str] | None = None) -> Path:
    """Return the nearest directory that looks like the project root.

    The search walks upwards from *start* (default: current working directory) until
    it finds any of the marker files/directories. If nothing matches, the original
    *start* directory is returned.
    """

    markers = tuple(markers) if markers is not None else ROOT_MARKERS
    current = (start or Path.cwd()).resolve()

    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in markers):
            return candidate

    return current


@dataclass(frozen=True)
class WorkflowResolution:
    """Resolved workflow metadata for running inside the simulator."""

    absolute_path: Path
    project_root: Path
    act_argument: str


def resolve_workflow_reference(workflow: Path, *, cwd: Path | None = None) -> WorkflowResolution:
    """Resolve *workflow* to an absolute path and derive act invocation metadata."""

    base = workflow if workflow.is_absolute() else (cwd or Path.cwd()) / workflow
    absolute = base.resolve()
    if not absolute.exists():
        raise FileNotFoundError(f"workflow file not found: {workflow}")

    project_root = find_project_root(absolute.parent)

    try:
        act_argument = str(absolute.relative_to(project_root))
    except ValueError:
        act_argument = str(absolute)

    return WorkflowResolution(
        absolute_path=absolute,
        project_root=project_root,
        act_argument=act_argument,
    )
