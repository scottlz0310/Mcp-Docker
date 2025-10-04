#!/bin/bash
# MCP Server Connection Test Script

set -e

echo "=== MCP Server Connection Test ==="
echo ""

# 1. Check if container is running
echo "1. Checking if mcp-github container is running..."
if docker ps --filter "name=mcp-github" --format "{{.Names}}" | grep -q "mcp-github"; then
    echo "✅ Container is running"
else
    echo "❌ Container is not running. Run 'make start' first."
    exit 1
fi

echo ""

# 2. Test MCP protocol communication
echo "2. Testing MCP protocol communication..."
RESPONSE=$(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | \
    docker exec -i mcp-github /server/github-mcp-server stdio 2>&1 | \
    grep -o '"serverInfo"' || echo "")

if [ -n "$RESPONSE" ]; then
    echo "✅ MCP server responds correctly"
else
    echo "❌ MCP server is not responding properly"
    exit 1
fi

echo ""

# 3. Check .mcp.json exists
echo "3. Checking if .mcp.json exists..."
if [ -f ".mcp.json" ]; then
    echo "✅ .mcp.json found"
else
    echo "❌ .mcp.json not found"
    exit 1
fi

echo ""

# 4. Validate .mcp.json syntax
echo "4. Validating .mcp.json syntax..."
if jq empty .mcp.json 2>/dev/null; then
    echo "✅ .mcp.json syntax is valid"
else
    echo "❌ .mcp.json has invalid JSON syntax"
    exit 1
fi

echo ""
echo "=== All tests passed! ==="
echo ""
echo "Next steps:"
echo "1. Open VS Code with Claude Code extension"
echo "2. Check Output panel (Ctrl+Shift+U) → 'Claude Code'"
echo "3. Look for MCP server initialization logs"
echo "4. Try using GitHub tools in Claude Code chat"
