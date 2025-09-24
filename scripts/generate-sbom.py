#!/usr/bin/env python3
"""SBOM (Software Bill of Materials) generation script"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_docker_image_info():
    """Get Docker image information"""
    try:
        result = subprocess.run(
            ["docker", "images", "--format", "json", "mcp-docker:latest"],
            capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout.strip())
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def get_base_image_packages():
    """Get packages from base image"""
    try:
        result = subprocess.run([
            "docker", "run", "--rm", "mcp-docker:latest",
            "sh", "-c", "apk list --installed 2>/dev/null || dpkg -l 2>/dev/null || rpm -qa 2>/dev/null"
        ], capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError:
        return []


def get_python_dependencies():
    """Get Python dependencies from pyproject.toml"""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        return []

    try:
        import tomllib
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        deps = data.get("project", {}).get("dependencies", [])
        dev_deps = data.get("dependency-groups", {}).get("dev", [])
        return deps + dev_deps
    except ImportError:
        # Fallback for older Python versions
        content = pyproject_path.read_text()
        deps = []
        in_deps = False
        for line in content.split('\n'):
            if 'dependencies = [' in line:
                in_deps = True
            elif in_deps and ']' in line:
                in_deps = False
            elif in_deps and '"' in line:
                dep = line.strip().strip(',').strip('"')
                if dep:
                    deps.append(dep)
        return deps


def generate_cyclonedx_sbom():
    """Generate CycloneDX SBOM format"""
    image_info = get_docker_image_info()
    python_deps = get_python_dependencies()

    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:mcp-docker-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now().isoformat() + "Z",
            "tools": [
                {
                    "vendor": "MCP Docker Team",
                    "name": "generate-sbom.py",
                    "version": "1.0.0"
                }
            ],
            "component": {
                "type": "container",
                "bom-ref": "mcp-docker",
                "name": "mcp-docker",
                "version": "0.1.0",
                "description": "Model Context Protocol (MCP) servers in Docker environment"
            }
        },
        "components": []
    }

    # Add Docker image as component
    if image_info:
        sbom["components"].append({
            "type": "container",
            "bom-ref": "mcp-docker-image",
            "name": "mcp-docker",
            "version": "latest",
            "description": "MCP Docker container image",
            "properties": [
                {"name": "docker:image:id", "value": image_info.get("ID", "")},
                {"name": "docker:image:size", "value": image_info.get("Size", "")},
                {"name": "docker:image:created", "value": image_info.get("CreatedAt", "")}
            ]
        })

    # Add Python dependencies
    for dep in python_deps:
        name = dep.split(">=")[0].split("==")[0].split("~=")[0]
        version = "unknown"
        if ">=" in dep:
            version = dep.split(">=")[1]
        elif "==" in dep:
            version = dep.split("==")[1]
        elif "~=" in dep:
            version = dep.split("~=")[1]

        sbom["components"].append({
            "type": "library",
            "bom-ref": f"python-{name}",
            "name": name,
            "version": version,
            "purl": f"pkg:pypi/{name}@{version}",
            "scope": "required"
        })

    return sbom


def generate_spdx_sbom():
    """Generate SPDX SBOM format"""
    python_deps = get_python_dependencies()

    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "mcp-docker-sbom",
        "documentNamespace": f"https://github.com/scottlz0310/mcp-docker/sbom-{datetime.now().strftime('%Y%m%d')}",
        "creationInfo": {
            "created": datetime.now().isoformat() + "Z",
            "creators": ["Tool: generate-sbom.py-1.0.0"]
        },
        "packages": [
            {
                "SPDXID": "SPDXRef-Package-mcp-docker",
                "name": "mcp-docker",
                "downloadLocation": "https://github.com/scottlz0310/mcp-docker",
                "filesAnalyzed": False,
                "licenseConcluded": "MIT",
                "licenseDeclared": "MIT",
                "copyrightText": "Copyright (c) 2025 MCP Docker Team"
            }
        ]
    }

    # Add Python dependencies as packages
    for i, dep in enumerate(python_deps, 2):
        name = dep.split(">=")[0].split("==")[0].split("~=")[0]
        sbom["packages"].append({
            "SPDXID": f"SPDXRef-Package-{name}",
            "name": name,
            "downloadLocation": f"https://pypi.org/project/{name}/",
            "filesAnalyzed": False,
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION"
        })

    return sbom


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Generate SBOM for MCP Docker")
    parser.add_argument("--format", choices=["cyclonedx", "spdx"], default="cyclonedx",
                       help="SBOM format (default: cyclonedx)")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")

    args = parser.parse_args()

    try:
        if args.format == "cyclonedx":
            sbom = generate_cyclonedx_sbom()
        else:
            sbom = generate_spdx_sbom()

        output = json.dumps(sbom, indent=2, ensure_ascii=False)

        if args.output:
            Path(args.output).write_text(output)
            print(f"✅ SBOM generated: {args.output}")
        else:
            print(output)

    except Exception as e:
        print(f"❌ Error generating SBOM: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
