# Self-Hosted Runner移行計画

**作成日時**: 2025-10-07 11:44:52 UTC
**対象**: GitHub Actions Simulator（act → Self-Hosted Runner）
**目的**: 軽量actベースからプロダクション対応Self-Hosted Runnerへの段階的移行

---

## 📋 移行概要

### 現状（actベース）
- **実行環境**: Docker内でactを使用した軽量シミュレーション
- **利点**: 高速起動、最小依存関係、開発者フレンドリー
- **制約**: 完全なGitHub Actions互換性なし、一部機能制限

### 移行後（Self-Hosted Runner）
- **実行環境**: GitHub公式Self-Hosted Runnerによる完全互換実行
- **利点**: 完全なGitHub Actions互換性、本番環境同等の動作保証
- **追加要件**: Runner登録・管理、セキュリティ強化、リソース管理

---

## Phase 1: 仕様策定・ドキュメント化・タスク管理

### 1.1 要件定義と設計

#### 機能要件
- **Runner登録管理**: GitHub App/Personal Access Token経由の自動登録
- **ワークフロー実行**: 完全なGitHub Actions互換性
- **マルチプラットフォーム**: Linux/macOS/Windows対応
- **スケーリング**: 複数Runner並列実行対応
- **監視・ログ**: 構造化ログ、メトリクス収集、ヘルスチェック

#### 非機能要件
- **セキュリティ**: 非rootユーザー実行、シークレット管理、ネットワーク分離
- **可用性**: 自動復旧、ヘルスチェック、障害検知
- **パフォーマンス**: 起動時間<30秒、メモリ使用量<2GB
- **保守性**: 自動更新、ログローテーション、設定管理

#### アーキテクチャ決定（ADR）

**ADR-001: Self-Hosted Runner実装方式**
- **決定**: Docker Compose + GitHub Actions Runner Controller (ARC)を採用
- **理由**:
  - Kubernetes不要で軽量
  - 既存Docker環境との統合容易
  - 自動スケーリング対応
- **代替案**:
  - ❌ 素のRunner: 管理複雑、スケーリング困難
  - ❌ Kubernetes + ARC: オーバースペック

**ADR-002: Runner登録方式**
- **決定**: GitHub App + Installation Token
- **理由**:
  - セキュリティ強化（短命トークン）
  - 組織レベル管理
  - 権限最小化
- **代替案**:
  - ❌ PAT: 長命トークン、権限過大

**ADR-003: 段階的移行戦略（独立サービス方式）**
- **決定**: Self-Hosted Runnerを独立した新サービスとして実装、act版と並行稼働後に削除
- **理由**:
  - 既存actサービスに影響なし（完全分離）
  - 検証期間中の安全な並行稼働
  - 不要時にサービスツリー全体を削除可能（クリーンな移行）
- **実装方式**:
  - 新サービス: `github-actions-runner`（docker-compose.ymlに追加）
  - 既存サービス: `actions-simulator`（act版、そのまま維持）
  - 削除時: サービス定義とディレクトリを一括削除
- **移行スケジュール**:
  - Phase 1-3: Runner新サービス実装（act併存）
  - Phase 4-6: 品質検証・ドキュメント整備
  - Phase 7: Runnerをデフォルト化、act非推奨
  - Phase 8: actサービス削除（サービス定義+ディレクトリ）

### 1.2 実装計画策定

#### 技術スタック
- **Runner**: GitHub Actions Runner (公式バイナリ)
- **コンテナ**: Docker + Docker Compose
- **言語**: Python 3.13+ (管理スクリプト)
- **設定管理**: YAML + 環境変数
- **監視**: 構造化ログ（JSON）、Prometheus metrics（オプション）

#### ディレクトリ構成（独立サービス方式）
```
Mcp-Docker/
├── services/
│   ├── actions-simulator/           # 既存actサービス（Phase 8で削除）
│   │   ├── Dockerfile
│   │   ├── scripts/
│   │   └── src/
│   └── github-actions-runner/       # 新規Runnerサービス
│       ├── Dockerfile
│       ├── scripts/
│       │   ├── setup.sh
│       │   ├── register.sh
│       │   └── start.sh
│       ├── src/
│       │   ├── runner_manager.py
│       │   ├── registration_service.py
│       │   └── health_monitor.py
│       └── config/
│           └── .env.template
├── docker-compose.yml               # 両サービス定義（Phase 8でact削除）
└── docs/
    └── runners/
        ├── MIGRATION_GUIDE.md
        ├── RUNNER_SETUP.md
        └── COMPARISON.md
```

#### リスク評価と対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| GitHub API制限 | 高 | レート制限監視、リトライ機構 |
| Runner登録失敗 | 高 | 自動リトライ、詳細エラーログ |
| セキュリティ侵害 | 高 | 非root実行、ネットワーク分離、シークレット暗号化 |
| リソース枯渇 | 中 | リソース制限、自動クリーンアップ |
| 既存ユーザー混乱 | 中 | 段階的移行、詳細ドキュメント |

### 1.3 タスクリスト作成と進捗管理

#### マイルストーン

**M1: 基盤実装（Phase 2）**
- [ ] Runnerコンテナ実装
- [ ] 登録スクリプト実装
- [ ] 基本起動確認

**M2: 機能完成（Phase 3）**
- [ ] ヘルスチェック実装
- [ ] 自動復旧機能
- [ ] ログ・監視統合

**M3: 品質保証（Phase 4-6）**
- [ ] セキュリティスキャン
- [ ] 統合テスト
- [ ] CI/CD統合

**M4: 移行完了（Phase 7-8）**
- [ ] ドキュメント完成
- [ ] ユーザー移行支援
- [ ] act非推奨化

#### タスク優先度

**P0（必須）**:
1. Runner登録・起動機能
2. セキュリティ基盤（非root、シークレット管理）
3. 基本ドキュメント

**P1（重要）**:
4. ヘルスチェック・自動復旧
5. 構造化ログ
6. 統合テスト

**P2（推奨）**:
7. マルチRunner対応
8. メトリクス収集
9. 移行ツール

### 1.4 Exit Criteria

- [x] ADR作成完了（ADR-001, 002, 003）
- [x] アーキテクチャ設計承認
- [x] リスク評価・対策策定完了
- [x] タスクリスト・マイルストーン設定完了
- [ ] 設計レビュー承認（レビュアー: プロジェクトオーナー）

---

## Phase 2: 実装段階・コミット管理・動作確認

### 2.1 基盤実装

#### ステップ1: Runnerコンテナ実装

**Dockerfile.runner**
```dockerfile
FROM ubuntu:22.04

# 非rootユーザー作成
RUN useradd -m -s /bin/bash runner

# 依存関係インストール
RUN apt-get update && apt-get install -y \
    curl jq git sudo \
    && rm -rf /var/lib/apt/lists/*

# Runner バイナリダウンロード
WORKDIR /home/runner
RUN curl -o actions-runner-linux-x64.tar.gz -L \
    https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz \
    && tar xzf actions-runner-linux-x64.tar.gz \
    && rm actions-runner-linux-x64.tar.gz

# 権限設定
RUN chown -R runner:runner /home/runner

USER runner
ENTRYPOINT ["/home/runner/run.sh"]
```

**docker-compose.yml（サービス追加）**
```yaml
services:
  # 既存actサービス（Phase 8で削除）
  actions-simulator:
    build:
      context: ./services/actions-simulator
    # ... 既存設定 ...

  # 新規Runnerサービス
  github-actions-runner:
    build:
      context: ./services/github-actions-runner
      dockerfile: Dockerfile
    container_name: mcp-github-runner
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_REPOSITORY=${GITHUB_REPOSITORY}
      - RUNNER_NAME=${RUNNER_NAME:-mcp-runner}
      - RUNNER_LABELS=${RUNNER_LABELS:-self-hosted,docker}
    volumes:
      - runner-work:/home/runner/_work
      - /var/run/docker.sock:/var/run/docker.sock
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    networks:
      - mcp-network

volumes:
  runner-work:
```

#### ステップ2: 登録スクリプト実装

**scripts/register-runner.sh**
```bash
#!/bin/bash
set -euo pipefail

# 環境変数チェック
: "${GITHUB_TOKEN:?GITHUB_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"

# 登録トークン取得
REGISTRATION_TOKEN=$(curl -s -X POST \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/runners/registration-token" \
  | jq -r .token)

# Runner設定
./config.sh \
  --url "https://github.com/${GITHUB_REPOSITORY}" \
  --token "${REGISTRATION_TOKEN}" \
  --name "${RUNNER_NAME:-mcp-runner}" \
  --labels "${RUNNER_LABELS:-self-hosted,docker}" \
  --unattended \
  --replace

echo "✅ Runner登録完了"
```

#### ステップ3: 起動スクリプト実装

**scripts/start-runner.sh**
```bash
#!/bin/bash
set -euo pipefail

echo "🚀 Self-Hosted Runner起動中..."

# 環境変数読み込み
if [ -f .env.runner ]; then
  export $(grep -v '^#' .env.runner | xargs)
fi

# Runner登録
./scripts/register-runner.sh

# Runner起動
./run.sh

echo "✅ Runner起動完了"
```

### 2.2 コミット・ブランチ戦略

**ブランチ**: `feature/self-hosted-runner-migration`

**コミット計画**:
1. `feat: Self-Hosted Runner基盤実装（Dockerfile, docker-compose）`
2. `feat: Runner登録・起動スクリプト実装`
3. `feat: 環境変数テンプレート追加`
4. `docs: Self-Hosted Runner基本ドキュメント追加`

### 2.3 起動確認・動作検証

**検証項目**:
- [ ] Dockerイメージビルド成功
- [ ] Runner登録成功（GitHub UI確認）
- [ ] Runner起動・待機状態確認
- [ ] 簡単なワークフロー実行成功

**検証コマンド**:
```bash
# Runnerサービスのみビルド
docker compose build github-actions-runner

# Runnerサービスのみ起動
docker compose up -d github-actions-runner

# ログ確認
docker compose logs -f github-actions-runner

# ヘルスチェック
docker compose ps github-actions-runner
```

### 2.4 Exit Criteria

- [ ] Runnerコンテナビルド成功
- [ ] Runner登録・起動確認完了
- [ ] 基本ワークフロー実行成功
- [ ] コードレビュー完了

---

## Phase 3: 機能検証・AI協調デバッグ

### 3.1 人間による機能検証

**検証シナリオ**:
1. **基本実行**: シンプルなワークフロー（echo, env確認）
2. **Docker操作**: Docker build/run実行
3. **複数ジョブ**: 並列ジョブ実行
4. **エラーハンドリング**: 失敗時の挙動確認
5. **再起動**: Runner再起動後の動作確認

### 3.2 AI協調でのデバッグ

**Amazon Q Developerセキュリティスキャン**:
- Dockerfile脆弱性チェック
- シークレット漏洩チェック
- 権限設定確認

### 3.3 統合テスト（動作確認用）

**tests/integration/test_runner_basic.bats**
```bash
#!/usr/bin/env bats

@test "Runner登録成功" {
  run docker compose -f docker-compose.runner.yml up -d
  [ "$status" -eq 0 ]
}

@test "Runnerヘルスチェック" {
  run docker compose -f docker-compose.runner.yml ps
  [[ "$output" =~ "Up" ]]
}

@test "簡単なワークフロー実行" {
  # GitHub API経由でワークフロートリガー
  run curl -X POST \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/workflows/test.yml/dispatches" \
    -d '{"ref":"main"}'
  [ "$status" -eq 0 ]
}
```

### 3.4 Exit Criteria

- [ ] 全検証シナリオ成功
- [ ] セキュリティスキャン問題なし
- [ ] 統合テスト成功
- [ ] ドキュメント更新完了

---

## Phase 4-8: 品質保証・CI/CD統合・移行完了

### Phase 4: リンティング・コード品質

**実施項目**:
- hadolint（Dockerfile.runner）
- shellcheck（全スクリプト）
- yamllint（docker-compose.runner.yml）
- Pythonコード品質チェック（ruff, mypy）

### Phase 5: テスト戦略・カバレッジ

**テスト構成**:
- ユニットテスト: Runner管理ロジック
- 統合テスト: Docker環境での動作確認
- E2Eテスト: 実際のワークフロー実行

**目標カバレッジ**: 80%以上

### Phase 6: CI/CD・自動化

**CI統合**:
```yaml
# .github/workflows/runner-ci.yml
name: Self-Hosted Runner CI

on:
  pull_request:
    paths:
      - 'runners/**'
      - 'docker-compose.runner.yml'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Runner Image
        run: docker compose -f docker-compose.runner.yml build
      - name: Run Tests
        run: make test-runner
```

### Phase 7: セキュリティ・品質保証

**セキュリティチェック**:
- Trivy（コンテナスキャン）
- Secret scanning
- 権限監査

### Phase 8: 移行完了・ドキュメント整備

**移行ドキュメント**:
- `docs/runners/MIGRATION_GUIDE.md`: act → Runner移行手順
- `docs/runners/RUNNER_SETUP.md`: Runner詳細セットアップ
- `docs/runners/COMPARISON.md`: act vs Runner機能比較表

**README更新**:
- Self-Hosted Runnerセクション追加
- クイックスタート更新
- トラブルシューティング追加

---

## 📊 移行スケジュール

| フェーズ | 期間 | 主要成果物 |
|---------|------|-----------|
| Phase 1 | 1週間 | ADR、設計書、タスクリスト |
| Phase 2 | 2週間 | 基盤実装、基本動作確認 |
| Phase 3 | 1週間 | 機能検証、統合テスト |
| Phase 4-6 | 2週間 | 品質保証、CI/CD統合 |
| Phase 7-8 | 1週間 | ドキュメント、移行完了 |
| **合計** | **7週間** | プロダクション対応Runner |

---

## 🔄 独立サービス併存戦略

### 併存期間（Phase 1-6）

**サービス選択方式**:
```bash
# actサービス起動（既存）
docker compose up -d actions-simulator

# Runnerサービス起動（新規）
docker compose up -d github-actions-runner

# 両方起動（検証期間）
docker compose up -d actions-simulator github-actions-runner
```

**Makefile統合**:
```makefile
actions-act:
	docker compose up -d actions-simulator

actions-runner:
	docker compose up -d github-actions-runner

actions: actions-runner  # デフォルトをRunnerに変更（Phase 7以降）
```

### 非推奨化（Phase 7）

**docker-compose.yml更新**:
```yaml
services:
  # 非推奨: Phase 8で削除予定
  # actions-simulator:
  #   build:
  #     context: ./services/actions-simulator

  # 推奨: デフォルトサービス
  github-actions-runner:
    # ...
```

**README更新**:
```markdown
## ⚠️ 重要なお知らせ

actサービスは非推奨となりました。Self-Hosted Runnerサービスへの移行を推奨します。

- **推奨**: `docker compose up -d github-actions-runner`
- **非推奨**: `docker compose up -d actions-simulator`（Phase 8で削除）
```

### actサービス削除（Phase 8）

**削除対象（一括削除）**:
```bash
# サービスディレクトリ削除
rm -rf services/actions-simulator/

# docker-compose.ymlからサービス定義削除
# actions-simulator セクション全体を削除

# 関連ドキュメント移動
mv docs/actions/ archive/docs/actions-simulator/
```

**保持対象**:
- 移行ガイド（`docs/runners/MIGRATION_GUIDE.md`）
- 比較ドキュメント（`docs/runners/COMPARISON.md`）

---

## 🎯 成功基準

### 技術的成功基準
- [ ] Runner登録成功率 > 99%
- [ ] ワークフロー実行成功率 > 95%
- [ ] 起動時間 < 30秒
- [ ] メモリ使用量 < 2GB
- [ ] セキュリティスキャン問題0件

### ユーザー体験成功基準
- [ ] セットアップ時間 < 5分
- [ ] ドキュメント完全性 > 90%
- [ ] ユーザー移行率 > 80%（Phase 7終了時）
- [ ] 問題報告 < 5件/月

### プロジェクト成功基準
- [ ] 全Phase完了
- [ ] CI/CD統合完了
- [ ] プロダクション品質達成
- [ ] コミュニティフィードバック反映

---

## 📚 参考資料

### 公式ドキュメント
- [GitHub Actions Self-Hosted Runners](https://docs.github.com/en/actions/hosting-your-own-runners)
- [Actions Runner Controller](https://github.com/actions/actions-runner-controller)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)

### 内部ドキュメント
- [docker-implementation-rules.md](.amazonq/rules/docker-implementation-rules.md)
- [docker-quality-rules.md](.amazonq/rules/docker-quality-rules.md)
- [README.md](README.md)

---

**次のアクション**: Phase 1 Exit Criteriaの設計レビュー承認を取得してください。
