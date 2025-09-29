#!/usr/bin/env bash
# Fix permissions for Docker containers (Non-interactive version)
# This script ensures that output directories have the correct permissions

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Get current user and group IDs
USER_ID="${USER_ID:-$(id -u)}"
GROUP_ID="${GROUP_ID:-$(id -g)}"

echo "🔧 Fixing permissions for Docker containers..."
echo "   User ID: ${USER_ID}"
echo "   Group ID: ${GROUP_ID}"

# Create directories if they don't exist
mkdir -p output/actions/summaries
mkdir -p output/actions/logs
mkdir -p logs

# Docker group check and setup
setup_docker_permissions() {
    echo "🐳 Checking Docker permissions..."

    # Test Docker access
    if docker version >/dev/null 2>&1; then
        echo "✅ Docker permissions OK"
        return 0
    fi

    echo "⚠️ Docker permission issue detected"

    # Check if user is in docker group
    if groups "$USER" | grep -q docker; then
        echo "✅ User is already in docker group"
        echo "💡 Try: newgrp docker"
        return 0
    fi

    # Check if docker group exists
    if ! getent group docker >/dev/null 2>&1; then
        echo "📦 Docker group not found"
        echo "💡 Manual setup required:"
        echo "   sudo groupadd docker"
        echo "   sudo usermod -aG docker $USER"
        echo "   newgrp docker"
        return 1
    fi

    echo "💡 Manual setup required:"
    echo "   sudo usermod -aG docker $USER"
    echo "   newgrp docker"
    return 1
}

# Try to fix ownership without sudo first
fix_ownership_safe() {
    echo "📁 Setting ownership for output directories..."

    # Try without sudo first
    if chown -R "${USER_ID}:${GROUP_ID}" output/ 2>/dev/null && \
       chown -R "${USER_ID}:${GROUP_ID}" logs/ 2>/dev/null; then
        echo "✅ Ownership set successfully"
        return 0
    fi

    # Check if we can use sudo without password
    if [ "${CI:-false}" != "true" ] && command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
        echo "🔐 Using sudo for ownership changes..."
        sudo chown -R "${USER_ID}:${GROUP_ID}" output/ logs/
        echo "✅ Ownership set with sudo"
        return 0
    fi

    # Fallback to chmod
    echo "📁 Setting permissions instead of ownership..."
    chmod -R 755 output/ logs/ 2>/dev/null || {
        chmod -R 777 output/ logs/
        echo "⚠️ Using 777 permissions as fallback"
    }
    echo "✅ Permissions set successfully"
    return 0
}

# Main execution
main() {
    # Setup Docker permissions if needed
    setup_docker_permissions || {
        echo "⚠️ Docker permission setup incomplete"
        echo "   Continuing with file permissions..."
    }

    # Fix file ownership/permissions
    fix_ownership_safe

    echo "✅ Permissions fixed successfully!"
}

main "$@"
