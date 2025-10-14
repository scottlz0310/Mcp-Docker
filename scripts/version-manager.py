#!/usr/bin/env python3
"""Version management script for MCP Docker Environment"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_current_version():
    """Get current version from pyproject.toml"""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found")

    content = pyproject_path.read_text()
    match = re.search(r'version = "([^"]+)"', content)
    if not match:
        raise ValueError("Version not found in pyproject.toml")

    return match.group(1)


def update_version(new_version):
    """Update version in pyproject.toml and main.py"""
    # Update pyproject.toml
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()
    content = re.sub(r'version = "[^"]+"', f'version = "{new_version}"', content)
    pyproject_path.write_text(content)

    # Update main.py if exists
    main_path = Path("main.py")
    if main_path.exists():
        content = main_path.read_text()
        content = re.sub(r'__version__ = "[^"]+"', f'__version__ = "{new_version}"', content)
        main_path.write_text(content)


def smart_check(target_version):
    """Smart version check with upgrade/downgrade detection"""
    current = get_current_version()

    print(f"Current version: {current}")
    print(f"Target version: {target_version}")

    # Version comparison using sort -V
    result = subprocess.run(
        ["sort", "-V"],
        input=f"{current}\n{target_version}\n",
        text=True,
        capture_output=True,
    )

    versions = result.stdout.strip().split("\n")

    if current == target_version:
        print("✅ Version unchanged")
        return True
    elif versions[0] == current:
        print(f"🔄 Version upgrade: {current} → {target_version}")
        return True
    else:
        print(f"❌ Version downgrade not allowed: {current} → {target_version}")
        return False


def update_changelog(version):
    """Update CHANGELOG.md with new version entry"""
    from datetime import datetime

    changelog_path = Path("CHANGELOG.md")

    if not changelog_path.exists():
        # Create basic CHANGELOG
        changelog_path.write_text("""# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

""")

    # Get git commits since last tag
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=True,
        )
        last_tag = result.stdout.strip()

        result = subprocess.run(
            ["git", "log", "--pretty=format:%s", f"{last_tag}..HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        commits = result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        # No previous tags
        result = subprocess.run(
            ["git", "log", "--pretty=format:%s"],
            capture_output=True,
            text=True,
            check=True,
        )
        commits = result.stdout.strip().split("\n") if result.stdout.strip() else []

    # Categorize commits
    features: list[str] = []
    fixes: list[str] = []
    docs: list[str] = []
    others: list[str] = []

    for commit in commits:
        if re.match(r"^feat(\(.+\))?: ", commit):
            features.append(re.sub(r"^feat(\(.+\))?: ", "- ", commit))
        elif re.match(r"^fix(\(.+\))?: ", commit):
            fixes.append(re.sub(r"^fix(\(.+\))?: ", "- ", commit))
        elif re.match(r"^docs(\(.+\))?: ", commit):
            docs.append(re.sub(r"^docs(\(.+\))?: ", "- ", commit))
        else:
            others.append(f"- {commit}")

    # Generate changelog entry
    date_str = datetime.now().strftime("%Y-%m-%d")

    entry = f"## [{version}] - {date_str}\n\n"

    if features:
        entry += "### ✨ 新機能\n" + "\n".join(features) + "\n\n"
    if fixes:
        entry += "### 🐛 修正\n" + "\n".join(fixes) + "\n\n"
    if docs:
        entry += "### 📝 ドキュメント\n" + "\n".join(docs) + "\n\n"
    if others:
        entry += "### 🔧 その他\n" + "\n".join(others) + "\n\n"

    if not any([features, fixes, docs, others]):
        entry += f"### 🔧 その他\n- リリース {version}\n\n"

    # Insert entry into CHANGELOG
    content = changelog_path.read_text()
    lines = content.split("\n")

    # Find insertion point (after header)
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("# Changelog"):
            # Skip header and find first empty line
            for j in range(i + 1, len(lines)):
                if lines[j].strip() == "":
                    insert_idx = j + 1
                    break
            break

    # Insert new entry
    lines.insert(insert_idx, entry.rstrip())
    changelog_path.write_text("\n".join(lines))

    print(f"✅ CHANGELOG updated for version {version}")


def main():
    parser = argparse.ArgumentParser(description="Version management for MCP Docker")
    parser.add_argument("--check", action="store_true", help="Show current version")
    parser.add_argument("--smart-check", metavar="VERSION", help="Smart version check")
    parser.add_argument("--update", metavar="VERSION", help="Update version")
    parser.add_argument("--update-changelog", metavar="VERSION", help="Update CHANGELOG")

    args = parser.parse_args()

    try:
        if args.check:
            version = get_current_version()
            print(f"Current version: {version}")

        elif args.smart_check:
            if not smart_check(args.smart_check):
                sys.exit(1)

        elif args.update:
            if smart_check(args.update):
                update_version(args.update)
                print(f"✅ Version updated to {args.update}")
            else:
                sys.exit(1)

        elif args.update_changelog:
            update_changelog(args.update_changelog)

        else:
            parser.print_help()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
