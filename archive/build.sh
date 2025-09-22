#!/bin/bash
set -e

echo "🔨 Building MCP Docker environment..."
docker-compose build --no-cache

echo "✅ Build completed!"
