#!/usr/bin/env python3
"""CLI wrapper for mcp-docker tool"""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Add the package root to sys.path
    package_root = Path(__file__).parent
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

    from main import main

    main()
