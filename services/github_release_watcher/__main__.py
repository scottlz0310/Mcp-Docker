"""
GitHub Release Watcher - モジュール実行エントリーポイント

Usage:
    python -m github-release-watcher [options]
"""

import sys

from .main import main

if __name__ == "__main__":
    sys.exit(main())
