#!/usr/bin/env bash
# Fix permissions for Docker containers
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

# Fix ownership
echo "📁 Setting ownership for output directories..."
sudo chown -R "${USER_ID}:${GROUP_ID}" output/ || {
    echo "⚠️ Could not change ownership with sudo, trying without..."
    chown -R "${USER_ID}:${GROUP_ID}" output/ 2>/dev/null || {
        echo "⚠️ Could not change ownership, setting permissions instead..."
        chmod -R 777 output/
    }
}

sudo chown -R "${USER_ID}:${GROUP_ID}" logs/ || {
    echo "⚠️ Could not change ownership with sudo, trying without..."
    chown -R "${USER_ID}:${GROUP_ID}" logs/ 2>/dev/null || {
        echo "⚠️ Could not change ownership, setting permissions instead..."
        chmod -R 777 logs/
    }
}

# Set permissions
echo "🔐 Setting permissions..."
chmod -R 755 output/
chmod -R 755 logs/

echo "✅ Permissions fixed successfully!"
