# Archived Sphinx Documentation Project

The files in this directory contain the retired Sphinx project that previously powered the auto-generated documentation for MCP Docker Environment.

- Original location: `docs/`
- Build command reference: `sphinx-build -b html . _build/html`
- Status: Archived (no longer built automatically)

To revive the documentation temporarily, install the former docs dependencies and run:

```bash
uv sync --group docs
uv run sphinx-build -b html archive/docs/sphinx archive/docs/sphinx/_build/html
```

> Note: the `docs` dependency group has been removed from `pyproject.toml`. You will need to install Sphinx packages manually or add them back before running the build commands above.
