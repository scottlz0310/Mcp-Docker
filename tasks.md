# タスク管理

現在の実装状況を踏まえた、今後の開発タスク一覧。

---

## 優先度高

### [#105] Makefile の整理（外部イメージ対応）

**状態**: 部分実装済み  
**関連 ISSUE**: [#105](https://github.com/scottlz0310/Mcp-Docker/issues/105)

docker-compose.yml はすべて外部イメージ参照に移行済み（ghcr.io・mcr.microsoft.com）。
Makefile の `crm-*` ターゲットがまだローカルビルド前提の実装のため整理が必要。

#### 残作業

- [ ] `CRM_IMAGE` デフォルト値を `ghcr.io/scottlz0310/copilot-review-mcp:latest` に変更（現在: `copilot-review-mcp:latest`）
- [ ] `crm-start` を `docker run` から `docker compose up -d copilot-review-mcp` に変更
- [ ] `crm-stop` / `crm-restart` を `docker compose stop/restart copilot-review-mcp` に変更
- [ ] `crm-build` ターゲット削除（ローカルビルド不要、ghcr.io イメージを使用）
- [ ] `make help` 説明文を現状に合わせて整理

#### スコープ外（今回やらないこと）

- Makefile ターゲット名のリネーム（`start-gateway` → `gh-start` 等）: 後方互換性を優先。Phase 2（services/ 削除）と同時に対応。

---

## 優先度中

### [#106] services/ ソースコードの段階的削除

**状態**: 保留（#105 安定確認後に着手）  
**関連 ISSUE**: [#106](https://github.com/scottlz0310/Mcp-Docker/issues/106)  
**前提**: #105 完了 + 外部イメージからの安定稼働（目安: 1〜2 週間）

#### 削除対象

| 対象 | 理由 |
|------|------|
| `services/copilot-review-mcp/` | `ghcr.io/scottlz0310/copilot-review-mcp` に移行済み |
| `services/github-oauth-proxy/` | `mcp-gateway`（外部リポジトリ）に移行済み |
| `docs/copilot-review-mcp-tasks.md` | 対象サービスのタスク管理ファイル（本ファイルに統合済み） |
| `Makefile` の `crm-build`、`CRM_DIR` 等ビルド関連 | ローカルビルド不要 |
| `.github/workflows/` の不要 CI | 外部リポジトリ側で管理 |

#### Makefile ターゲット名リネーム（#106 と同時）

| 旧 | 新 | 備考 |
|----|----|----|
| `start-gateway` | `start`（デフォルト化）| 全サービス起動を標準に |
| `logs-gateway` | `logs`（全体）| |
| `status-gateway` | 削除（`status` に統合）| |
| `crm-start` | 削除（`start` に統合）| |

---

## バックログ（検討中）

### renovate: services/ 配下の依存更新を停止

`services/copilot-review-mcp/go.mod` 等は削除予定のため、
Renovate の更新対象から外すか `ignorePaths` を設定する。

---

## 完了済み（参考）

- [x] docker-compose.yml を外部 ghcr.io イメージ参照に移行（mcp-gateway, copilot-review-mcp）（#105 部分完了）
- [x] playwright-mcp を auth=none パターンとして追加（#109/#110）
- [x] mcp-gateway, copilot-review-mcp の ghcr.io パッケージを public に公開
- [x] copilot-review-mcp: async watch + notification ベース再設計（#63〜#68）
- [x] workflow-lint ワークフロー追加（#94 暫定対応）
- [x] Codecov upload step の secrets 直参照を修正（#94 暫定対応）
