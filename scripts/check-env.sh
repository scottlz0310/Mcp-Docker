#!/bin/bash

echo "🔍 Environment Variables Check"
echo "=============================="

# .bashrcから読み込み
# shellcheck disable=SC1090,SC1091
source ~/.bashrc

if [ -n "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
    echo "✅ GITHUB_PERSONAL_ACCESS_TOKEN: Set in .bashrc"
else
    echo "❌ GITHUB_PERSONAL_ACCESS_TOKEN: Not found in .bashrc"
fi

if [ -f .env ]; then
    echo "📄 .env file: Found"
    if grep -q "GITHUB_PERSONAL_ACCESS_TOKEN" .env; then
        echo "✅ GITHUB_PERSONAL_ACCESS_TOKEN: Set in .env"
    fi
else
    echo "📄 .env file: Not found"
fi

echo ""
echo "Priority: .bashrc > .env > .env.template"
