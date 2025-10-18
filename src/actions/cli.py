#!/usr/bin/env python3
"""GitHub Actions Simulator CLI"""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Main CLI entry point for actions simulator"""
    # Get project root
    project_root = Path(__file__).parent.parent.parent

    # Build command using run-actions.sh
    script_path = project_root / "scripts" / "run-actions.sh"

    if not script_path.exists():
        print(f"Error: {script_path} not found", file=sys.stderr)
        sys.exit(1)

    # Pass all arguments to the script
    cmd = [str(script_path)] + sys.argv[1:]

    try:
        result = subprocess.run(cmd, cwd=str(project_root))
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
