#!/usr/bin/env python3
"""CLI wrapper for mcp-docker tool"""

import sys
from pathlib import Path


def main() -> None:
    """Main entry point for mcp-docker CLI"""
    # Add the package root to sys.path
    package_root = Path(__file__).parent
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

    # Import and run the main CLI
    from main import main as main_cli

    main_cli()


if __name__ == "__main__":
    main()
