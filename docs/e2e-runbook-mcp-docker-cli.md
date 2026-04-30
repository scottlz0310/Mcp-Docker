# mcp-docker CLI E2E テストランブック

`mcp-docker register` コマンドが各 IDE CLI の MCP 設定ファイルに正しく書き込まれることを手動で確認する手順書。

---

## 前提条件

| 項目 | 確認コマンド |
|------|------------|
| `mcp-docker` バイナリ（ビルド済み） | `./mcp-docker --help` |
| Docker Compose スタック起動済み | `make status` |
| 確認したい IDE CLI のインストール | 各セクション参照 |

---

## ステップ 0: バイナリビルド

```bash
# リポジトリルートで実行
go build -o mcp-docker ./cmd/mcp-docker

# ヘルプ確認
./mcp-docker --help
```

**期待出力:**
```
mcp-docker は MCP Docker の補助ワークフローを管理します。

使い方:
  mcp-docker register [--agent claude|copilot|codex|all] [--compose path] [--external path] [--yes] [--dry-run]
```

---

## ステップ 1: dry-run で登録計画を確認

```bash
./mcp-docker register --dry-run --yes
```

**期待出力例（サーバーが 3 件の場合）:**
```
claude の dry-run 計画:
- 既存登録確認: claude mcp list
- copilot-review:
  - 既存登録があれば削除: claude mcp remove --scope user copilot-review
  - 追加: claude mcp add --transport http --scope user copilot-review http://127.0.0.1:8080/mcp/copilot-review
- github:
  - 既存登録があれば削除: claude mcp remove --scope user github
  - 追加: claude mcp add --transport http --scope user github http://127.0.0.1:8080/mcp/github
- playwright:
  - 既存登録があれば削除: claude mcp remove --scope user playwright
  - 追加: claude mcp add --transport http --scope user playwright http://127.0.0.1:8080/mcp/playwright
copilot の dry-run 計画:
...
codex の dry-run 計画:
...
```

**確認ポイント:**
- [ ] 各エージェントの計画が出力される
- [ ] `--compose docker-compose.yml` からサーバー一覧が正しく読み込まれる
- [ ] URL が `http://127.0.0.1:8080/mcp/<name>` 形式になっている

---

## ステップ 2: Claude Code への登録確認

> **前提:** `claude` CLI がインストールされていること (`claude --version`)

### 2-1. 登録前の状態確認

```bash
claude mcp list
```

**記録:** 登録前のサーバー一覧をメモしておく。

### 2-2. 登録実行

```bash
./mcp-docker register --agent claude --yes
```

**期待動作:**
- 既存の同名サーバーがあれば削除してから追加
- エラーなく完了する

### 2-3. 登録後の確認

```bash
claude mcp list
```

**確認ポイント:**
- [ ] `github`、`copilot-review`、`playwright` が一覧に表示される
- [ ] `transport: http` で登録されている

### 2-4. Claude Code で実際に MCP 接続確認

```
Claude Code を起動 → /mcp または Tools メニューで MCP サーバー一覧を確認
```

**確認ポイント:**
- [ ] `github` サーバーが緑（接続済み）で表示される
- [ ] `copilot-review` サーバーが緑で表示される

---

## ステップ 3: GitHub Copilot CLI への登録確認

> **前提:** `gh` CLI + `gh copilot` 拡張がインストールされていること

### 3-1. 登録前の状態確認

```bash
gh copilot -- mcp list
```

### 3-2. 登録実行

```bash
./mcp-docker register --agent copilot --yes
```

### 3-3. 登録後の確認

```bash
gh copilot -- mcp list
```

**確認ポイント:**
- [ ] `github`、`copilot-review`、`playwright` が一覧に表示される

---

## ステップ 4: Codex への登録確認

> **前提:** `codex` CLI がインストールされていること (`codex --version`)

### 4-1. 登録前の状態確認

```bash
codex mcp list
```

### 4-2. 登録実行

```bash
./mcp-docker register --agent codex --yes
```

### 4-3. 登録後の確認

```bash
codex mcp list
```

**確認ポイント:**
- [ ] `github`、`copilot-review`、`playwright` が一覧に表示される

---

## ステップ 5: 全エージェントまとめて登録

```bash
./mcp-docker register --yes
```

**確認ポイント:**
- [ ] claude・copilot・codex すべてにエラーなく登録される
- [ ] 重複登録しても正常終了する（冪等性）

---

## ステップ 6: external サーバーの追加確認

`config/mcp-external.yml` にサーバーを追記して動作確認する。

```yaml
# config/mcp-external.yml 追記例
servers:
  - name: my-custom-server
    url: http://127.0.0.1:9090/mcp
```

```bash
./mcp-docker register --dry-run --yes
```

**確認ポイント:**
- [ ] `my-custom-server` が dry-run 計画に含まれる

---

## エラーケース確認

| シナリオ | 実行コマンド | 期待動作 |
|---------|------------|---------|
| docker-compose.yml が存在しない | `./mcp-docker register --compose missing.yml --yes` | エラーで終了 |
| 不明なエージェント | `./mcp-docker register --agent unknown --yes` | エラーで終了 |
| サーバー名の重複 | docker-compose と external に同名サーバーを設定 | エラーで終了 |

---

## チェックリスト（最終確認）

- [ ] ステップ 0: バイナリビルド成功
- [ ] ステップ 1: dry-run 出力が正しい
- [ ] ステップ 2: Claude Code に登録・接続確認
- [ ] ステップ 3: Copilot CLI に登録確認
- [ ] ステップ 4: Codex に登録確認（任意）
- [ ] ステップ 5: 全エージェント一括登録・冪等性確認
- [ ] ステップ 6: external サーバー追加確認（任意）
