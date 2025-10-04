# Dockerfile統合計画

## 現状分析

### 現在の構成

プロジェクトには2つのDockerfileが存在：

1. **Dockerfile** (2,726 bytes)
   - ベースイメージ: `node:24-alpine`
   - 主な用途: GitHub MCPサーバー
   - 含まれるもの: Node.js 24, GitHub MCP server, act CLI, Python 3, uv

2. **Dockerfile.actions** (3,130 bytes)
   - ベースイメージ: `python:3.13-slim`
   - 主な用途: GitHub Actions Simulator
   - 含まれるもの: Python 3.13, act CLI, uv, テストツール

### 問題点

1. **コードの重複**
   - 両方のファイルでact CLIをインストール
   - 両方のファイルでuvをインストール
   - 同じソースコードをコピー

2. **保守性の低下**
   - 依存関係の更新を2箇所で行う必要がある
   - バージョン不整合のリスク
   - .actrcの設定が古い（`act-latest` vs `runner-latest`）

3. **設計の矛盾**
   - GitHub MCPサーバーもPythonコードを使用しているのにNode.jsベース
   - datetime-validatorサービスはDockerfile（Node.jsベース）を使用しているがPythonで書かれている

## 影響範囲

### 1. docker-compose.yml

**現在の使用箇所:**

```yaml
services:
  github-mcp:
    build: .                    # Dockerfileを使用

  datetime-validator:
    build: .                    # Dockerfileを使用

  actions-simulator:
    build:
      dockerfile: Dockerfile.actions  # 3箇所で使用

  actions-server:
    build:
      dockerfile: Dockerfile.actions

  actions-shell:
    build:
      dockerfile: Dockerfile.actions
```

**影響:** 3つのサービス（actions-simulator, actions-server, actions-shell）のbuild設定を変更する必要がある

### 2. Makefile

**現在のビルドターゲット:**

```makefile
build:                      # すべてのイメージをビルド
  - docker compose build
  - docker compose --profile tools build actions-simulator
  - docker compose --profile debug build actions-server

build-actions:              # Actions Simulatorのみ
  - docker compose --profile tools build actions-simulator

build-actions-server:       # Actions Serverのみ
  - docker compose --profile debug build actions-server
```

**影響:** ビルドコマンド自体は変更不要（docker-compose.ymlの変更で対応）

### 3. GitHub Actions CI/CDワークフロー

**影響を受けるワークフロー:**

- `.github/workflows/ci.yml` - Dockerfileの変更検出、ビルドキャッシュ
- `.github/workflows/quality-gates.yml` - Dockerビルド検証
- `.github/workflows/security.yml` - Dockerイメージセキュリティスキャン
- `.github/workflows/template-validation.yml` - Docker compose検証

**影響:** キャッシュキーの調整が必要
```yaml
# 現在
key: ${{ runner.os }}-buildx-${{ hashFiles('Dockerfile', 'docker-compose.yml') }}

# 統合後
key: ${{ runner.os }}-buildx-${{ hashFiles('Dockerfile', 'docker-compose.yml') }}
# 同じだが、Dockerfile.actionsの削除を反映
```

## 統合戦略

### アプローチ1: マルチステージビルド（推奨）

**単一のDockerfileでマルチターゲット:**

```dockerfile
# ベース: Python 3.13
FROM python:3.13-slim AS base

# 共通の依存関係インストール
RUN apt-get update && apt-get install -y \
    bash curl git jq nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# ビルダーステージ
FROM base AS builder
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
COPY . /app
WORKDIR /app
RUN uv sync

# GitHub MCPサーバー用ターゲット
FROM base AS mcp-server
RUN npm install -g @modelcontextprotocol/server-github
COPY --from=builder /app /app
CMD ["node", "/usr/local/lib/node_modules/@modelcontextprotocol/server-github/dist/index.js"]

# Actions Simulator用ターゲット
FROM base AS actions-simulator
RUN curl -fsSL https://github.com/nektos/act/releases/download/v0.2.69/act_Linux_x86_64.tar.gz \
    | tar -xz -C /usr/local/bin
COPY --from=builder /app /app
COPY .actrc /home/actions/.actrc
USER actions
CMD ["uv", "run", "python", "main.py", "actions", "--help"]
```

### アプローチ2: 完全統合（シンプル）

**1つのイメージで全機能:**

すべてのサービスが同じイメージを使用し、コマンドで動作を切り替える

**メリット:**
- 最もシンプル
- イメージの再利用性が高い

**デメリット:**
- イメージサイズが大きくなる
- 不要な依存関係が含まれる

## 推奨: 段階的移行プラン

### フェーズ1: 準備（影響範囲の最小化）

1. **新しいDockerfileを作成**
   - `Dockerfile.unified` として作成
   - マルチステージビルドで実装
   - 既存のDockerfileは残す

2. **テスト環境での検証**
   ```bash
   # ターゲットを指定してビルド
   docker build --target mcp-server -t mcp-unified:test .
   docker build --target actions-simulator -t actions-unified:test .

   # 動作確認
   docker run mcp-unified:test
   docker run actions-unified:test
   ```

### フェーズ2: 段階的な切り替え

1. **docker-compose.ymlに新しい設定を追加**
   ```yaml
   services:
     github-mcp-unified:
       build:
         context: .
         dockerfile: Dockerfile.unified
         target: mcp-server
       # 既存のgithub-mcpと並行運用
   ```

2. **ローカルテスト**
   - 開発者が新しいイメージで動作確認
   - 問題があれば元に戻せる

### フェーズ3: 本番適用

1. **docker-compose.ymlの切り替え**
   ```yaml
   services:
     github-mcp:
       build:
         context: .
         dockerfile: Dockerfile  # 新しいDockerfileに変更
         target: mcp-server      # ターゲット指定
   ```

2. **CIワークフローの更新**
   - キャッシュキーの調整
   - ビルドステップの確認

3. **古いDockerfileの削除**
   - `Dockerfile` → 新しい統合版に置き換え
   - `Dockerfile.actions` → 削除

## 移行チェックリスト

### 事前準備
- [x] 現在のDockerfile、Dockerfile.actionsをバックアップ
- [x] 統合Dockerfileを作成
- [x] ローカルでビルドテスト成功

### テスト
- [x] github-mcpサービスが起動する
- [x] datetime-validatorサービスが起動する
- [x] actions-simulatorサービスが起動する
- [x] actions-serverサービスが起動する
- [x] actions-shellサービスが起動する
- [x] `make actions-run INDEX=1` が成功する

### CI/CD
- [x] ci.ymlのビルドが成功する（キャッシュキー確認済み）
- [x] quality-gates.ymlのビルドが成功する
- [x] security.ymlのセキュリティスキャンが成功する
- [x] キャッシュが正常に機能する

### 本番適用
- [x] docker-compose.ymlを更新
- [x] Makefileの動作確認（必要なら更新）
- [x] READMEのビルド手順を更新
- [x] 古いDockerfileを削除
- [x] コミット & プッシュ

## リスクと軽減策

### リスク1: ビルド失敗
**軽減策:** 段階的移行により、いつでも元に戻せる状態を維持

### リスク2: イメージサイズの増加
**軽減策:** マルチステージビルドで最小限のレイヤーのみコピー

### リスク3: 依存関係の競合
**軽減策:** ベースイメージをPython 3.13に統一し、Node.jsは必要最小限のバージョンを追加

## 次のアクション

1. **Dockerfile.unifiedの作成** - マルチステージビルドで実装
2. **ローカルテスト** - 各サービスの動作確認
3. **docker-compose.yml更新** - 新しいビルド設定に切り替え
4. **CI動作確認** - ワークフローが正常に動作するか確認
5. **ドキュメント更新** - README等のビルド手順を更新
6. **古いファイル削除** - Dockerfile.actionsを削除

## 期待される効果

1. **保守性の向上**
   - 依存関係の更新が1箇所で完結
   - バージョン不整合のリスク排除

2. **ビルド時間の短縮**
   - 共通レイヤーの再利用によるキャッシュ効率化

3. **開発体験の改善**
   - シンプルな構成で理解しやすい
   - 新規開発者のオンボーディング容易化

4. **将来の拡張性**
   - 新しいサービス追加時も統一されたパターンで対応可能

---

## 📋 実施結果（2025-10-03完了）

### 成果サマリー

✅ **完了日**: 2025年10月3日
✅ **コミット**: 661531f "refactor: Dockerfileを統合してマルチステージビルドに移行"
✅ **変更**: 13 files changed, 674 insertions(+), 212 deletions(-)

### 実装内容

#### 統合Dockerfile（236行）
- **base**: Python 3.13 + 基本ツール
- **base-with-node**: Node.js 20を追加
- **builder**: Python依存関係ビルド
- **act-installer**: act CLIインストール
- **mcp-server**: GitHub MCPサーバー（Node.js 20 + Python）
- **datetime-validator**: DateTime検証サービス
- **actions-simulator**: GitHub Actions Simulator

#### 主な改善
1. Node.js 20使用（catthehacker/ubuntu:runner-latest）
2. setup-uv@v6の互換性問題を解決
3. --pull=falseでネットワークタイムアウト回避
4. .cacheディレクトリを除外してRuffチェックを最適化
5. hadolint警告を修正（SHELL pipefail設定）

### 検証結果

✅ すべてのサービスがビルド成功
✅ `make actions-run INDEX=1` で Job succeeded
✅ 全pre-commitフックが通過
✅ ビルドキャッシュが効率的に動作

### 削除されたファイル
- `Dockerfile.actions` - 統合Dockerfileに置き換え

### 追加されたファイル
- `.clinerules/dockerfile-consolidation-plan.md` - この統合計画ドキュメント
- `services/actions/path_utils.py` - パス解決ロジック

### 期待通りの効果を確認
- ✅ 保守性向上: 依存関係の更新が1箇所で完結
- ✅ ビルド効率化: 共通レイヤーのキャッシュで高速ビルド
- ✅ 一貫性: すべてのサービスが同じベースを使用
- ✅ 最新化: Node.js 20、最新の依存関係
