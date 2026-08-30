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
    $(error Git for Windows bash.exe is required on Windows. \
      Install Git for Windows and retry, or specify: GIT_BASH=<path/to/bash.exe>)
  endif
  SHELL       := $(GIT_BASH)
  .SHELLFLAGS := -c
  BASH_CMD    := $(GIT_BASH)
  export LANG   := C.UTF-8
  export LC_ALL := C.UTF-8
else
  BASH_CMD    := bash
endif

# 環境変数優先、.env フォールバック（安全な awk テキスト抽出）
# include .env は Makefile として解釈される危険があり、
# . ./.env (shell source) は .env 内の任意コマンドを実行する危険がある。
# awk でテキスト解析のみ行い KEY=VALUE 行から値を取り出す（コマンド実行なし）。
# ?= はシェルの export 済み変数を優先するので、環境変数が設定済みの場合は .env を無視する。
ENV_GET = $(strip $(shell awk -v key='$(1)' '/^[[:space:]]*#/{next} $$0 ~ ("^[[:space:]]*" key "[[:space:]]*=") {val=substr($$0,index($$0,"=")+1); gsub(/^[[:space:]"'"'"']+|[[:space:]"'"'"']+$$/,"",val); print val; exit}' .env 2>/dev/null))
ifneq (,$(wildcard .env))
  OAUTH_CLIENT_ID              ?= $(call ENV_GET,OAUTH_CLIENT_ID)
  OAUTH_CLIENT_SECRET          ?= $(call ENV_GET,OAUTH_CLIENT_SECRET)
  GITHUB_CLIENT_ID             ?= $(call ENV_GET,GITHUB_CLIENT_ID)
  GITHUB_CLIENT_SECRET         ?= $(call ENV_GET,GITHUB_CLIENT_SECRET)
  GITHUB_MCP_CLIENT_ID         ?= $(call ENV_GET,GITHUB_MCP_CLIENT_ID)
  GITHUB_MCP_CLIENT_SECRET     ?= $(call ENV_GET,GITHUB_MCP_CLIENT_SECRET)
  GITHUB_APP_ID                ?= $(call ENV_GET,GITHUB_APP_ID)
  GITHUB_APP_INSTALLATION_ID   ?= $(call ENV_GET,GITHUB_APP_INSTALLATION_ID)
  MCP_GATEWAY_INTERNAL_SECRET  ?= $(call ENV_GET,MCP_GATEWAY_INTERNAL_SECRET)
  MCP_GATEWAY_PORT             ?= $(call ENV_GET,MCP_GATEWAY_PORT)
  MCP_GATEWAY_PUBLIC_URL       ?= $(call ENV_GET,MCP_GATEWAY_PUBLIC_URL)
  MCP_GATEWAY_BASE_URL         ?= $(call ENV_GET,MCP_GATEWAY_BASE_URL)
endif

# OAUTH_* → GITHUB_MCP_* → GITHUB_* の優先順位でフォールバック解決
ifeq ($(strip $(OAUTH_CLIENT_ID)),)
  OAUTH_CLIENT_ID := $(or $(GITHUB_MCP_CLIENT_ID),$(GITHUB_CLIENT_ID))
endif
ifeq ($(strip $(OAUTH_CLIENT_SECRET)),)
  OAUTH_CLIENT_SECRET := $(or $(GITHUB_MCP_CLIENT_SECRET),$(GITHUB_CLIENT_SECRET))
endif
# 子プロセス（docker compose / mcp-docker register）に確実に渡す
export OAUTH_CLIENT_ID OAUTH_CLIENT_SECRET GITHUB_CLIENT_ID GITHUB_CLIENT_SECRET GITHUB_APP_ID GITHUB_APP_INSTALLATION_ID MCP_GATEWAY_INTERNAL_SECRET MCP_GATEWAY_PORT MCP_GATEWAY_PUBLIC_URL MCP_GATEWAY_BASE_URL

.DEFAULT_GOAL := help

.PHONY: help
help: ## 利用可能なターゲット一覧を表示
	@printf "Available targets:\n\n"
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | awk -F ':|##' '{printf "  %-20s %s\n", $$1, $$3}'

# ----------------------------------------
# サービス管理
# ----------------------------------------

.PHONY: check-github-app-config
check-github-app-config:
	$(if $(and $(OAUTH_CLIENT_ID),$(OAUTH_CLIENT_SECRET)),,$(error ERROR: OAUTH_CLIENT_ID / OAUTH_CLIENT_SECRET are required for the GitHub App (legacy: GITHUB_MCP_CLIENT_ID / GITHUB_MCP_CLIENT_SECRET). Set them in .env or as environment variables.))
	$(if $(and $(GITHUB_APP_ID),$(GITHUB_APP_INSTALLATION_ID)),,$(error ERROR: GITHUB_APP_ID / GITHUB_APP_INSTALLATION_ID are required for GitHub App installation authentication. Set them in .env or as environment variables.))
	$(if $(MCP_GATEWAY_INTERNAL_SECRET),,$(error ERROR: MCP_GATEWAY_INTERNAL_SECRET is required for credential diagnostics. Set a random value of at least 32 characters.))
	$(if $(wildcard config/github-app/private-key.pem),,$(error ERROR: config/github-app/private-key.pem is required. Download the GitHub App private key and place it at this path.))

.PHONY: start-gateway
start-gateway: check-github-app-config ## 全サービスを mcp-gateway 経由で起動（127.0.0.1:8080）
	# --remove-orphans: リネーム前の copilot-review-mcp など compose 定義外の旧コンテナを除去
	docker compose up -d --remove-orphans github-mcp review-raven thread-owl mcp-gateway playwright-mcp
	@echo "Started mcp-gateway endpoint: $(or $(MCP_GATEWAY_PUBLIC_URL),$(MCP_GATEWAY_BASE_URL),http://127.0.0.1:$(or $(MCP_GATEWAY_PORT),8080))"

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

SERVICE ?= mcp-gateway

.PHONY: health-check
health-check: ## サービスのヘルスチェック（GitHub App credential 診断込み）
	"$(BASH_CMD)" ./scripts/health-check.sh --service "$(SERVICE)" --with-api

.PHONY: health-check-quick
health-check-quick: ## サービスのヘルスチェック（credential 診断をスキップ）
	"$(BASH_CMD)" ./scripts/health-check.sh --service "$(SERVICE)" --no-api

MCP_CONFORMANCE_GATEWAY_URL = $(patsubst %/,%,$(or $(MCP_GATEWAY_PUBLIC_URL),$(MCP_GATEWAY_BASE_URL),http://127.0.0.1:$(or $(MCP_GATEWAY_PORT),8080)))
MCP_CONFORMANCE_TOKEN_ENV ?= MCP_E2E_BEARER_TOKEN
MCP_CONFORMANCE_TIMEOUT ?= 45s

.PHONY: mcp-conformance
mcp-conformance: mcp-conformance-thread-owl mcp-conformance-review-raven ## MCP 2026-07-28 conformance を全対象routeで実行

.PHONY: mcp-conformance-thread-owl
mcp-conformance-thread-owl: $(MCP_DOCKER) ## thread-owl route のdiscovery/resource/subscription ackを検証
	$(MCP_DOCKER) conformance \
		--url "$(MCP_CONFORMANCE_GATEWAY_URL)/mcp/thread-owl" \
		--token-env "$(MCP_CONFORMANCE_TOKEN_ENV)" \
		--resource-uri "queue://review/queue" \
		--require-no-buffering \
		--timeout "$(MCP_CONFORMANCE_TIMEOUT)"

.PHONY: mcp-conformance-review-raven
mcp-conformance-review-raven: $(MCP_DOCKER) ## review-raven route のdiscovery/stateless tool経路を検証
	$(MCP_DOCKER) conformance \
		--url "$(MCP_CONFORMANCE_GATEWAY_URL)/mcp/review-raven" \
		--token-env "$(MCP_CONFORMANCE_TOKEN_ENV)" \
		--timeout "$(MCP_CONFORMANCE_TIMEOUT)"

.PHONY: pull-gateway
pull-gateway: ## 全サービスの Docker イメージを取得
	docker compose pull

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

# :main イメージ
# docker-compose.yml のデフォルトは :latest（mcp-gateway v0.9.0 で builtin AS / TLS 終端とも収録済み）。
# mcp-gateway / review-raven / thread-owl の :latest はリリース時のみ更新されるため、
# リリース前の最新 main ブランチビルドを使いたい場合はこれらのターゲットを使用する。
# ?= により環境変数・make コマンドライン引数での上書きが可能
# 例: make pull-main MCP_GATEWAY_MAIN_IMAGE=ghcr.io/scottlz0310/mcp-gateway:edge
MCP_GATEWAY_MAIN_IMAGE       ?= ghcr.io/scottlz0310/mcp-gateway:main
REVIEW_RAVEN_MAIN_IMAGE ?= ghcr.io/scottlz0310/review-raven:main
THREAD_OWL_MAIN_IMAGE ?= ghcr.io/scottlz0310/thread-owl:main

.PHONY: pull-main
pull-main: ## 最新開発版イメージを取得（リリース前 main ブランチビルド）
	docker compose pull github-mcp
	GITHUB_MCP_GATEWAY_IMAGE=$(MCP_GATEWAY_MAIN_IMAGE) \
	REVIEW_RAVEN_IMAGE=$(REVIEW_RAVEN_MAIN_IMAGE) \
	THREAD_OWL_IMAGE=$(THREAD_OWL_MAIN_IMAGE) \
	docker compose pull mcp-gateway review-raven thread-owl
ifeq ($(OS),Windows_NT)
	@echo $$'\u2713 :main \u30a4\u30e1\u30fc\u30b8\u3092\u53d6\u5f97\u3057\u307e\u3057\u305f\u3002\u8d77\u52d5: make start-main'
else
	@echo "✓ :main イメージを取得しました。起動: make start-main"
endif

.PHONY: start-main
start-main: check-github-app-config ## 最新開発版イメージで全サービスを起動
	GITHUB_MCP_GATEWAY_IMAGE=$(MCP_GATEWAY_MAIN_IMAGE) \
	REVIEW_RAVEN_IMAGE=$(REVIEW_RAVEN_MAIN_IMAGE) \
	THREAD_OWL_IMAGE=$(THREAD_OWL_MAIN_IMAGE) \
	docker compose up -d --remove-orphans github-mcp review-raven thread-owl mcp-gateway playwright-mcp
	@echo "Started mcp-gateway endpoint (main build): $(or $(MCP_GATEWAY_PUBLIC_URL),$(MCP_GATEWAY_BASE_URL),http://127.0.0.1:$(or $(MCP_GATEWAY_PORT),8080))"

.PHONY: restart-main
restart-main: stop-gateway start-main ## 最新開発版イメージで全サービスを再起動

# CLI 登録（Primary）
BIN_DIR      := bin
EXE_EXT      :=
ifeq ($(OS),Windows_NT)
  EXE_EXT    := .exe
endif
MCP_DOCKER   := $(BIN_DIR)/mcp-docker$(EXE_EXT)
GO_SOURCES   := $(shell find cmd internal -name '*.go' 2>/dev/null)
REGISTER_FLAGS ?=
VERSION ?= 2.16.3
GO_LDFLAGS ?= -X main.version=$(VERSION)

$(MCP_DOCKER): go.mod go.sum $(GO_SOURCES)
	"$(SHELL)" -c "mkdir -p $(BIN_DIR)"
	go build -ldflags "$(GO_LDFLAGS)" -o $(MCP_DOCKER) ./cmd/mcp-docker

.PHONY: register
register: $(MCP_DOCKER) ## 対話的に IDE/CLI と MCP サーバーを選択して登録
	$(MCP_DOCKER) register $(REGISTER_FLAGS)

.PHONY: register-claude
register-claude: $(MCP_DOCKER) ## Claude CLI に MCP サーバーを登録
	$(MCP_DOCKER) register --agent claude $(REGISTER_FLAGS)

.PHONY: register-copilot
register-copilot: $(MCP_DOCKER) ## GitHub Copilot CLI に MCP サーバーを登録
	$(MCP_DOCKER) register --agent copilot $(REGISTER_FLAGS)

.PHONY: register-codex
register-codex: $(MCP_DOCKER) ## Codex CLI に MCP サーバーを登録
	$(MCP_DOCKER) register --agent codex $(REGISTER_FLAGS)

.PHONY: register-antigravity
register-antigravity: $(MCP_DOCKER) ## Antigravity CLI に MCP サーバーを登録
	$(MCP_DOCKER) register --agent antigravity $(REGISTER_FLAGS)

.PHONY: register-all
register-all: $(MCP_DOCKER) ## Claude / Copilot / Codex / Antigravity CLI に MCP サーバーを登録
	$(MCP_DOCKER) register --agent all $(REGISTER_FLAGS)

# ----------------------------------------
# 開発
# ----------------------------------------

.PHONY: lint
lint: lint-shell lint-go ## すべてのLint実行（シェルスクリプト lint + Go vet）

.PHONY: test-go
test-go: ## Go CLI のテスト実行
	go test ./...

.PHONY: build-go
build-go: $(MCP_DOCKER) ## Go CLI をビルド

.PHONY: lint-shell
lint-shell: ## シェルスクリプトのlint実行
	"$(BASH_CMD)" ./scripts/lint-shell.sh

.PHONY: lint-go
lint-go: ## Go 静的解析（golangci-lint + go vet フォールバック）
	@if command -v golangci-lint >/dev/null 2>&1; then \
		golangci-lint run ./...; \
	else \
		echo 'golangci-lint not found, falling back to go vet'; \
		go vet ./...; \
	fi

.PHONY: test-shell
test-shell: ## シェルスクリプトのテスト実行
	@if command -v bats >/dev/null 2>&1; then \
		bats tests/shell/*.bats; \
	else \
		echo "bats is not installed"; \
		echo "   Install: brew install bats-core"; \
		exit 1; \
	fi

# ----------------------------------------
# TLS セットアップ
# ----------------------------------------

.PHONY: setup-tls
setup-tls: ## Windows ホスト上に TLS 証明書と CA をセットアップし、.env を更新
	"$(BASH_CMD)" ./scripts/require-pwsh.sh
	pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/setup-tls.ps1

# ----------------------------------------
# クレデンシャル管理
# ----------------------------------------

.PHONY: rotate-secret
rotate-secret: ## credential ローテーション後に永続 config を消去して再起動（tokens.db は保持）
	docker compose down
	"$(BASH_CMD)" ./scripts/rotate-secret.sh
	$(MAKE) start-gateway

# ----------------------------------------
# クリーンアップ
# ----------------------------------------

.PHONY: clean
clean: ## 一時ファイル削除
ifeq ($(OS),Windows_NT)
	@echo $$'\u30ad\u30e3\u30c3\u30b7\u30e5\u3092\u30af\u30ea\u30fc\u30f3\u30a2\u30c3\u30d7\u4e2d...'
else
	@echo "キャッシュをクリーンアップ中..."
endif
	rm -rf .tmp test-results coverage.out
ifeq ($(OS),Windows_NT)
	@echo $$'\u30ad\u30e3\u30c3\u30b7\u30e5\u30af\u30ea\u30fc\u30f3\u30a2\u30c3\u30d7\u5b8c\u4e86'
else
	@echo "キャッシュクリーンアップ完了"
endif

.PHONY: clean-docker
clean-docker: ## Dockerリソースクリーンアップ
ifeq ($(OS),Windows_NT)
	@echo $$'Docker\u30ea\u30bd\u30fc\u30b9\u3092\u30af\u30ea\u30fc\u30f3\u30a2\u30c3\u30d7\u4e2d...'
else
	@echo "Dockerリソースをクリーンアップ中..."
endif
	docker compose down -v
	docker system prune -f
ifeq ($(OS),Windows_NT)
	@echo $$'Docker\u30af\u30ea\u30fc\u30f3\u30a2\u30c3\u30d7\u5b8c\u4e86'
else
	@echo "Dockerクリーンアップ完了"
endif

.PHONY: clean-all
clean-all: clean clean-docker ## 全てクリーンアップ
ifeq ($(OS),Windows_NT)
	@echo $$'\u3059\u3079\u3066\u306e\u30af\u30ea\u30fc\u30f3\u30a2\u30c3\u30d7\u5b8c\u4e86'
else
	@echo "すべてのクリーンアップ完了"
endif
