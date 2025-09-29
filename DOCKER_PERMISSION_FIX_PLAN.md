# Docker権限問題の修正計画

## 問題の概要

`make actions`実行時にDocker権限エラーが発生し、手動でsudoパスワード入力が必要になっています。

### 🔍 特定された問題

1. **Docker Socket権限**: `/var/run/docker.sock`への接続権限不足
2. **sudo要求**: `fix-permissions.sh`でsudoパスワードが必要
3. **Docker-in-Docker**: コンテナ内からのDocker実行権限問題

### 📋 エラーログ分析

```bash
Error: permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock
```

## 修正提案

### 1. Docker権限の自動設定

#### 現在の`fix-permissions.sh`の問題
```bash
sudo chown -R "${USER_ID}:${GROUP_ID}" output/
```
- sudoパスワードが必要
- 非対話的実行ができない

#### 修正版`fix-permissions.sh`
```bash
#!/usr/bin/env bash
# Fix permissions for Docker containers (Non-interactive version)

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
    echo "🐳 Setting up Docker permissions..."

    # Check if user is in docker group
    if groups "$USER" | grep -q docker; then
        echo "✅ User is already in docker group"
        return 0
    fi

    # Check if docker group exists
    if ! getent group docker >/dev/null 2>&1; then
        echo "📦 Creating docker group..."
        if command -v sudo >/dev/null 2>&1; then
            sudo groupadd docker
        else
            echo "⚠️ Cannot create docker group without sudo"
            return 1
        fi
    fi

    # Add user to docker group (requires sudo)
    echo "👤 Adding user to docker group..."
    if command -v sudo >/dev/null 2>&1; then
        sudo usermod -aG docker "$USER"
        echo "✅ User added to docker group"
        echo "⚠️ Please log out and log back in for changes to take effect"
        echo "   Or run: newgrp docker"
        return 0
    else
        echo "⚠️ Cannot add user to docker group without sudo"
        return 1
    fi
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

    # Try with sudo if available and not in CI
    if [ "${CI:-false}" != "true" ] && command -v sudo >/dev/null 2>&1; then
        echo "🔐 Requesting sudo for ownership changes..."
        if sudo -n true 2>/dev/null; then
            # Sudo without password
            sudo chown -R "${USER_ID}:${GROUP_ID}" output/ logs/
            echo "✅ Ownership set with sudo"
            return 0
        else
            # Sudo requires password
            echo "⚠️ Sudo password required for ownership changes"
            echo "   You can skip this by running: chmod -R 777 output/ logs/"
            read -p "   Continue with sudo? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                sudo chown -R "${USER_ID}:${GROUP_ID}" output/ logs/
                echo "✅ Ownership set with sudo"
                return 0
            fi
        fi
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
    if ! docker version >/dev/null 2>&1; then
        echo "🐳 Docker permission issue detected"
        setup_docker_permissions || {
            echo "⚠️ Docker permission setup failed"
            echo "   Manual steps:"
            echo "   1. sudo groupadd docker"
            echo "   2. sudo usermod -aG docker $USER"
            echo "   3. newgrp docker"
        }
    else
        echo "✅ Docker permissions OK"
    fi

    # Fix file ownership/permissions
    fix_ownership_safe

    echo "✅ Permissions fixed successfully!"
}

main "$@"
```

### 2. Makefileの改善

#### 現在の問題
```makefile
./scripts/fix-permissions.sh; \
```
- 権限エラーで停止する
- 非対話的実行ができない

#### 修正版Makefile（actionsターゲット）
```makefile
actions:
	@echo "🎭 GitHub Actions Simulator - インタラクティブ実行"
	@workflows=$$(find .github/workflows -name "*.yml" -o -name "*.yaml" 2>/dev/null); \
	if [ -z "$$workflows" ]; then \
		echo "❌ ワークフローファイルが見つかりません"; \
		exit 1; \
	fi; \
	default_selection=".github/workflows/ci.yml"; \
	echo "📋 使用可能なワークフロー:"; \
	echo "$$workflows" | nl -w2 -s') '; \
	echo ""; \
	echo "🚀 デフォルト実行: CI ワークフロー"; \
	echo ""; \
	selected=""; \
	if [ -n "$(WORKFLOW)" ]; then \
		if [ -f "$(WORKFLOW)" ]; then \
			selected="$(WORKFLOW)"; \
		else \
			match=$$(echo "$$workflows" | grep -Fx "$(WORKFLOW)"); \
			if [ -z "$$match" ]; then \
				echo "❌ 指定された WORKFLOW が一覧に見つかりません: $(WORKFLOW)"; \
				exit 1; \
			fi; \
			selected="$$match"; \
		fi; \
	elif [ -n "$(INDEX)" ]; then \
		if ! echo "$(INDEX)" | grep -Eq '^[0-9]+$$'; then \
			echo "❌ INDEX は数値で指定してください"; \
			exit 1; \
		fi; \
		selected=$$(echo "$$workflows" | sed -n "$(INDEX)p"); \
		if [ -z "$$selected" ]; then \
			echo "❌ INDEX が範囲外です: $(INDEX)"; \
			exit 1; \
		fi; \
	else \
		echo "💡 Enter だけで $$default_selection を実行します"; \
		printf "🎯 実行するワークフローを選択してください (Enter=1): "; \
		read choice; \
		if [ -z "$$choice" ]; then \
			choice=1; \
		fi; \
		if ! echo "$$choice" | grep -Eq '^[0-9]+$$'; then \
			echo "❌ 無効な選択です"; \
			exit 1; \
		fi; \
		selected=$$(echo "$$workflows" | sed -n "$${choice}p"); \
		if [ -z "$$selected" ]; then \
			echo "❌ 無効な番号です"; \
			exit 1; \
		fi; \
	fi; \
	if [ -z "$$selected" ]; then \
		selected="$$default_selection"; \
	fi; \
	echo ""; \
	echo "🚀 実行ワークフロー: $$selected"; \
	echo ""; \
	echo "🔧 Preparing environment..."; \
	./scripts/fix-permissions.sh || echo "⚠️ Permission setup completed with warnings"; \
	echo "🐳 Starting Docker container..."; \
	USER_ID=$$(id -u) GROUP_ID=$$(id -g) docker compose --profile tools run --rm \
		-e WORKFLOW_FILE="$$selected" \
		-e ACT_LOG_LEVEL=info \
		-e ACT_PLATFORM=ubuntu-latest=catthehacker/ubuntu:act-latest \
		-e DOCKER_HOST=unix:///var/run/docker.sock \
		-v /var/run/docker.sock:/var/run/docker.sock:rw \
		actions-simulator \
		uv run python main.py actions simulate "$$selected" $$(if $(VERBOSE),--verbose,) $$(if $(JOB),--job $(JOB),)
```

### 3. Docker Compose設定の改善

#### 現在の問題
- Docker socket権限が不適切
- ユーザーID/グループIDの設定が不完全

#### 修正版docker-compose.yml（actions-simulatorサービス）
```yaml
services:
  actions-simulator:
    build:
      context: .
      dockerfile: Dockerfile
      target: actions-simulator
    profiles: ["tools"]
    user: "${USER_ID:-1000}:${GROUP_ID:-1000}"
    volumes:
      - .:/app:rw
      - /var/run/docker.sock:/var/run/docker.sock:rw
      - ./output:/app/output:rw
      - ./logs:/app/logs:rw
    environment:
      - PYTHONPATH=/app
      - ACTIONS_SIMULATOR_VERBOSE=true
      - ACT_LOG_LEVEL=${ACT_LOG_LEVEL:-info}
      - ACT_PLATFORM=${ACT_PLATFORM:-ubuntu-latest=catthehacker/ubuntu:act-latest}
      - DOCKER_HOST=unix:///var/run/docker.sock
      - USER_ID=${USER_ID:-1000}
      - GROUP_ID=${GROUP_ID:-1000}
    working_dir: /app
    group_add:
      - "${DOCKER_GID:-999}"  # Docker group ID
    security_opt:
      - no-new-privileges:true
    cap_add:
      - DAC_OVERRIDE  # For file permission handling
    networks:
      - mcp-network
```

### 4. 環境変数設定スクリプト

#### 新規作成: `scripts/setup-docker-env.sh`
```bash
#!/usr/bin/env bash
# Setup Docker environment variables

set -euo pipefail

# Get Docker group ID
DOCKER_GID=$(getent group docker | cut -d: -f3 2>/dev/null || echo "999")

# Export environment variables
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)
export DOCKER_GID="${DOCKER_GID}"

echo "🔧 Docker環境変数設定:"
echo "   USER_ID=${USER_ID}"
echo "   GROUP_ID=${GROUP_ID}"
echo "   DOCKER_GID=${DOCKER_GID}"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cat > .env << EOF
# Docker Environment Variables
USER_ID=${USER_ID}
GROUP_ID=${GROUP_ID}
DOCKER_GID=${DOCKER_GID}

# Actions Simulator Settings
ACT_LOG_LEVEL=info
ACT_PLATFORM=ubuntu-latest=catthehacker/ubuntu:act-latest
ACTIONS_SIMULATOR_VERBOSE=true
EOF
    echo "✅ .env ファイルを作成しました"
else
    echo "ℹ️ .env ファイルは既に存在します"
fi
```

## 実装手順

### Phase 1: 緊急修正（即座に実装）
1. ✅ `fix-permissions.sh`の非対話化
2. ✅ Makefileのエラーハンドリング改善
3. ✅ Docker権限の自動設定

### Phase 2: 根本修正（1日以内）
1. 🔄 Docker Compose設定の改善
2. 🔄 環境変数設定の自動化
3. 🔄 権限問題の完全解決

### Phase 3: 最適化（1週間以内）
1. 🔮 Docker-in-Docker最適化
2. 🔮 CI/CD環境での自動化
3. 🔮 ドキュメント更新

## 検証方法

### 1. 修正後のテスト
```bash
# 権限設定のテスト
./scripts/fix-permissions.sh

# Docker権限のテスト
docker version

# make actionsのテスト
make actions WORKFLOW=.github/workflows/quality-gates.yml
```

### 2. 複数環境での検証
- ✅ 新しいユーザー環境
- ✅ Docker未設定環境
- ✅ CI/CD環境
- ✅ 権限制限環境

## 期待される効果

### 🎯 改善効果
1. **非対話的実行**: sudoパスワード不要
2. **自動権限設定**: Docker権限の自動解決
3. **エラー回復**: 権限問題の自動修復

### 📊 測定指標
- sudo要求回数: 現在 100% → 目標 0%
- 実行成功率: 現在 < 50% → 目標 > 95%
- セットアップ時間: 50%短縮を目標

---

**作成日時**: 2025-09-29 11:35:00 UTC
**優先度**: 最高（即座に修正が必要）
**担当**: Docker Integration Team
