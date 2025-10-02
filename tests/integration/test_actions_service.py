#!/usr/bin/env python3
"""Regression tests for the GitHub Actions workflow parser utilities."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from services.actions.workflow_parser import WorkflowParseError, WorkflowParser


class TestWorkflowParser:
    """Parser behaviour verification suite."""

    def setup_method(self) -> None:
        self.parser = WorkflowParser()

    def test_parse_simple_workflow(self) -> None:
        workflow_content = (
            "name: Test Workflow\n"
            '"on": [push]\n'
            "jobs:\n"
            "  test:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            '      - run: echo "Hello World"\n'
        )

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yml",
            delete=False,
        ) as handle:
            handle.write(workflow_content)
            temp_path = Path(handle.name)

        try:
            workflow_data = self.parser.parse_file(temp_path)
            assert workflow_data["name"] == "Test Workflow"
            assert "push" in workflow_data["on"]
            assert "test" in workflow_data["jobs"]
        finally:
            temp_path.unlink()

    def test_parse_invalid_yaml(self) -> None:
        invalid_content = (
            "name: Invalid\n"
            '"on": [push]\n'
            "jobs:\n"
            "  test:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            '      - run: echo "test"\n'
            "    invalid_indent_here\n"
            "    another_problem: ]\n"
        )

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yml",
            delete=False,
        ) as handle:
            handle.write(invalid_content)
            temp_path = Path(handle.name)

        try:
            with pytest.raises(WorkflowParseError):
                self.parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_parse_missing_required_fields(self) -> None:
        incomplete_content = (
            'name: Incomplete\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo "test"\n'
        )

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yml",
            delete=False,
        ) as handle:
            handle.write(incomplete_content)
            temp_path = Path(handle.name)

        try:
            with pytest.raises(WorkflowParseError):
                self.parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_parse_nonexistent_file(self) -> None:
        nonexistent_path = Path("/tmp/nonexistent_workflow.yml")

        with pytest.raises(WorkflowParseError):
            self.parser.parse_file(nonexistent_path)


def test_strict_validate_rejects_missing_jobs(tmp_path: Path) -> None:
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text(
        "name: Missing Jobs\n'on': [push]\n",
        encoding="utf-8",
    )

    parser = WorkflowParser()

    with pytest.raises(WorkflowParseError):
        parser.parse_file(workflow_file)


def test_workflow_parser_supports_matrix_strategy(tmp_path: Path) -> None:
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text(
        (
            "name: Matrix Workflow\n"
            "on: [push]\n"
            "jobs:\n"
            "  build:\n"
            "    runs-on: ubuntu-latest\n"
            "    strategy:\n"
            "      matrix:\n"
            '        python: ["3.11", "3.12"]\n'
            "    steps:\n"
            '      - run: echo "${{ matrix.python }}"\n'
        ),
        encoding="utf-8",
    )

    parser = WorkflowParser()
    workflow = parser.parse_file(workflow_file)

    simulator_meta = workflow.get("_simulator", {}).get("matrix", {})
    expansions = simulator_meta.get("expansions", {})
    base_lookup = simulator_meta.get("base_lookup", {})

    variant_ids = expansions.get("build")
    assert variant_ids == ["build__python-3-11", "build__python-3-12"]
    assert all(base_lookup[variant_id] == "build" for variant_id in variant_ids)

    for variant_id, expected_python in zip(
        variant_ids,
        ["3.11", "3.12"],
        strict=True,
    ):
        job = workflow["jobs"][variant_id]
        assert job["matrix"]["python"] == expected_python
