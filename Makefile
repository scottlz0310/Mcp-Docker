# ========================================
# MCP Gateway スタック - サービス管理
# ========================================

# Windows では GNU Make のデフォルトシェル (cmd.exe) が Unix コマンド非対応のため
# Git for Windows の bash を使用する。
# GIT_BASH にフルパスを設定することで任意のインストール先を使用可能。
#   例: make GIT_BASH="C:/Tools/Git/bin/bash.exe"
ifeq ($(OS),Windows_NT)
  GIT_BASH ?=
  ifeq ($(strip $(GIT_BASH)),)
    # 代表的なインストール先を 8.3 短縮パスで検索（パス内スペースを回避）
    GIT_BASH := $(firstword $(wildcard \
      C:/PROGRA~1/Git/bin/bash.exe \
      C:/PROGRA~2/Git/bin/bash.exe \
      D:/PROGRA~1/Git/bin/bash.exe \
      D:/PROGRA~2/Git/bin/bash.exe))
  endif
  ifeq ($(strip $(GIT_BASH)),)
    $(error Windows では Git for Windows の bash.exe が必要です。\
      インストール後に再実行するか GIT_BASH=<bash.exeのフルパス> を指定してください)
  endif
  SHELL       := $(GIT_BASH)
  .SHELLFLAGS := -c
endif

# 環境変数優先、.env フォールバック（安全な awk テキスト抽出）
# include .env は Makefile として解釈される危険があり、
# . ./.env (shell source) は .env 内の任意コマンドを実行する危険がある。
# awk でテキスト解析のみ行い KEY=VALUE 行から値を取り出す（コマンド実行なし）。
# ?= はシェルの export 済み変数を優先するので、環境変数が設定済みの場合は .env を無視する。
ENV_GET = $(strip $(shell awk -v key='$(1)' '/^[[:space:]]*#/{next} $$0 ~ ("^[[:space:]]*" key "[[:space:]]*=") {val=substr($$0,index($$0,"=")+1); gsub(/^[[:space:]"'"'"']+|[[:space:]"'"'"']+$$/,"",val); print val; exit}' .env 2>/dev/null))
ifneq (,$(wildcard .env))
  GITHUB_CLIENT_ID             ?= $(call ENV_GET,GITHUB_CLIENT_ID)
  GITHUB_CLIENT_SECRET         ?= $(call ENV_GET,GITHUB_CLIENT_SECRET)
  GITHUB_MCP_CLIENT_ID         ?= $(call ENV_GET,GITHUB_MCP_CLIENT_ID)
  GITHUB_MCP_CLIENT_SECRET     ?= $(call ENV_GET,GITHUB_MCP_CLIENT_SECRET)
  GITHUB_PERSONAL_ACCESS_TOKEN ?= $(call ENV_GET,GITHUB_PERSONAL_ACCESS_TOKEN)
  BASE_URL                     ?= $(call ENV_GET,BASE_URL)
  GITHUB_OAUTH_SCOPES          ?= $(call ENV_GET,GITHUB_OAUTH_SCOPES)
  MCP_GATEWAY_PORT             ?= $(call ENV_GET,MCP_GATEWAY_PORT)
endif

# mcp-gateway 向け変数が空または未設定なら既存 OAuth 変数をフォールバック利用
ifeq ($(strip $(GITHUB_MCP_CLIENT_ID)),)
  GITHUB_MCP_CLIENT_ID := $(GITHUB_CLIENT_ID)
endif
ifeq ($(strip $(GITHUB_MCP_CLIENT_SECRET)),)
  GITHUB_MCP_CLIENT_SECRET := $(GITHUB_CLIENT_SECRET)
endif
# 子プロセス（docker compose）に確実に渡す
export GITHUB_CLIENT_ID GITHUB_CLIENT_SECRET GITHUB_MCP_CLIENT_ID GITHUB_MCP_CLIENT_SECRET GITHUB_PERSONAL_ACCESS_TOKEN BASE_URL GITHUB_OAUTH_SCOPES MCP_GATEWAY_PORT

.DEFAULT_GOAL := help

.PHONY: help
help: ## 利用可能なターゲット一覧を表示
	@printf "Available targets:\n\n"
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | awk -F ':|##' '{printf "  %-20s %s\n", $$1, $$3}'

# ----------------------------------------
# サービス管理
# ----------------------------------------

.PHONY: start-gateway
start-gateway: ## 全サービスを mcp-gateway 経由で起動（localhost:8080）
	$(if $(and $(GITHUB_MCP_CLIENT_ID),$(GITHUB_MCP_CLIENT_SECRET)),,$(error ERROR: GITHUB_MCP_CLIENT_ID / GITHUB_MCP_CLIENT_SECRET must be set in .env or environment))
	$(if $(and $(GITHUB_CLIENT_ID),$(GITHUB_CLIENT_SECRET)),,$(error ERROR: GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET must be set in .env or environment (required by copilot-review-mcp)))
	docker compose up -d github-mcp copilot-review-mcp mcp-gateway playwright-mcp
	@echo "Started mcp-gateway endpoint: http://127.0.0.1:$(or $(MCP_GATEWAY_PORT),8080)"

.PHONY: stop-gateway
stop-gateway: ## 全サービスを停止
	docker compose down

.PHONY: restart-gateway
restart-gateway: stop-gateway start-gateway ## 全サービスを再起動

.PHONY: logs-gateway
logs-gateway: ## mcp-gateway のログ表示
	docker compose logs -f mcp-gateway

.PHONY: status-gateway
status-gateway: ## 全サービスの状態確認
	docker compose ps

.PHONY: pull-gateway
pull-gateway: ## 全サービスの Docker イメージを取得
	docker compose pull

.PHONY: prepare
prepare: ## 環境整備のみ実行（.env作成・事前確認）
	./scripts/setup.sh --prepare-only

# 後方互換エイリアス
.PHONY: stop
stop: stop-gateway ## 全サービスを停止（stop-gateway のエイリアス）

.PHONY: restart
restart: restart-gateway ## 全サービスを再起動（restart-gateway のエイリアス）

.PHONY: logs
logs: logs-gateway ## mcp-gateway ログ表示（logs-gateway のエイリアス）

.PHONY: pull
pull: pull-gateway ## 全サービスの Docker イメージを取得（pull-gateway のエイリアス）

.PHONY: status
status: status-gateway ## 全サービスの状態確認（status-gateway のエイリアス）

# ----------------------------------------
# 設定生成
# ----------------------------------------

.PHONY: gen-config
gen-config: ## IDE設定ファイルを生成 (IDE=vscode|claude-desktop|kiro|amazonq|codex|copilot-cli)
	./scripts/generate-ide-config.sh --ide $(or $(IDE),vscode)

# ----------------------------------------
# 開発
# ----------------------------------------

.PHONY: lint
lint: lint-shell ## すべてのLint実行

.PHONY: lint-shell
lint-shell: ## シェルスクリプトのlint実行
	./scripts/lint-shell.sh

.PHONY: test-shell
test-shell: ## シェルスクリプトのテスト実行
	@if command -v bats >/dev/null 2>&1; then \
		bats tests/shell/*.bats; \
	else \
		echo "❌ bats がインストールされていません"; \
		echo "   インストール: brew install bats-core"; \
		exit 1; \
	fi

# ----------------------------------------
# クリーンアップ
# ----------------------------------------

.PHONY: clean
clean: ## 一時ファイル削除
	@echo "キャッシュをクリーンアップ中..."
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage test-results
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "キャッシュクリーンアップ完了"

.PHONY: clean-docker
clean-docker: ## Dockerリソースクリーンアップ
	@echo "Dockerリソースをクリーンアップ中..."
	docker compose down -v
	docker system prune -f
	@echo "Dockerクリーンアップ完了"

.PHONY: clean-all
clean-all: clean clean-docker ## 全てクリーンアップ
	@echo "すべてのクリーンアップ完了"
