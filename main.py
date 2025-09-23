#!/usr/bin/env python3
"""MCP Docker Environment - Main entry point"""

import sys
import subprocess
import os
from pathlib import Path

__version__ = "0.1.0"


def main():
    """Main entry point for MCP Docker services"""
    if len(sys.argv) < 2:
        print("Usage: python main.py <service>")
        print("Available services: github, datetime, codeql")
        print(f"Version: {__version__}")
        sys.exit(1)

    service = sys.argv[1]

    if service == "--version" or service == "-v":
        print(f"MCP Docker Environment v{__version__}")
        sys.exit(0)

    if service == "github":
        # GitHub MCP Server
        cmd = ["python", "-m", "mcp_server_github"]
    elif service == "datetime":
        # DateTime Validator
        cmd = ["python", "services/datetime/datetime_validator.py"]
    elif service == "codeql":
        # CodeQL Analysis
        print("CodeQL analysis not implemented yet")
        sys.exit(1)
    else:
        print(f"Unknown service: {service}")
        sys.exit(1)

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Service {service} failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        print(f"Service {service} not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
