# GitHub Actions Docker Simulator - 技術設計書

## 概要

GitHub ActionsのワークフローをDockerベースでローカル環境で事前実行・検証できるCIシミュレーション機能を実装します。この機能により、実際のGitHub Actionsにプッシュする前に、ローカル環境でワークフローの動作確認、デバッグ、最適化が可能になります。

## 背景・目的

### 課題
- GitHub Actionsの実行は時間がかかり、デバッグサイクルが非効率
- ワークフロー実行にはGitHub APIコール制限やビルド時間の制約がある
- 本番環境でしかテストできない設定ミスの早期発見が困難

### 目標
- ローカル環境でのGitHub Actions完全シミュレーション
- 高速なフィードバックループの実現
- ワークフロー設定ミスの事前検出
- 既存MCPインフラストラクチャとの統合

## アーキテクチャ設計

### 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions Simulator                │
├─────────────────────────────────────────────────────────────┤
│  CLI Interface                 │  Web UI (Optional)          │
├─────────────────────────────────────────────────────────────┤
│                  Workflow Parser & Validator               │
├─────────────────────────────────────────────────────────────┤
│  Job Orchestrator  │  Environment Manager │  Result Aggregator│
├─────────────────────────────────────────────────────────────┤
│            Docker Container Runtime Engine                  │
├─────────────────────────────────────────────────────────────┤
│                    Docker Network Bridge                   │
├─────────────────────────────────────────────────────────────┤
│  Runner Container 1 │ Runner Container 2 │ Runner Container N │
└─────────────────────────────────────────────────────────────┘
```

### コンポーネント構成

#### 1. Workflow Parser & Validator
- **目的**: GitHub Actionsワークフローファイル（.yml/.yaml）の解析・検証
- **機能**:
  - YAML構文解析
  - GitHub Actions仕様準拠性チェック
  - セマンティック検証（依存関係、権限等）
  - 環境変数・シークレット解決

#### 2. Job Orchestrator
- **目的**: ワークフロージョブの実行制御・スケジューリング
- **機能**:
  - 依存関係に基づく実行順序制御
  - 並列実行管理
  - ジョブ間データ共有（artifacts）
  - 実行状態管理（running, success, failure, cancelled）

#### 3. Environment Manager
- **目的**: 実行環境の構築・管理
- **機能**:
  - Dockerイメージの動的選択・構築
  - 環境変数・シークレットの注入
  - ボリュームマウント管理
  - ネットワーク設定

#### 4. Container Runtime Engine
- **目的**: Docker コンテナでの実際のワークフロー実行
- **機能**:
  - ランナー環境のコンテナ起動
  - ステップ実行管理
  - ログ収集・転送
  - リソース制限・監視

#### 5. Result Aggregator
- **目的**: 実行結果の集約・レポート生成
- **機能**:
  - 実行ログの統合
  - 成功/失敗状況の集約
  - HTML/JSON形式のレポート生成
  - 実行時間・リソース使用量統計

## 技術仕様

### サポート対象

#### GitHub Actions機能
- ✅ **基本ワークフロー**: on, jobs, steps
- ✅ **ランナー指定**: ubuntu-latest, ubuntu-20.04, ubuntu-22.04
- ✅ **アクション実行**: uses, run
- ✅ **環境変数**: env (global, job, step level)
- ✅ **条件分岐**: if, needs
- ✅ **マトリックス戦略**: strategy.matrix
- ⚠️ **部分対応**: secrets（ローカルファイルから読み込み）
- ❌ **未対応**:
  - GitHub固有サービス（GitHub Container Registry等）
  - セルフホステッドランナー固有機能
  - GitHub App認証

#### Dockerランナー環境
```yaml
# サポートするランナーイメージ
runners:
  ubuntu-latest: "ghcr.io/catthehacker/ubuntu:act-latest"
  ubuntu-22.04: "ghcr.io/catthehacker/ubuntu:act-22.04"
  ubuntu-20.04: "ghcr.io/catthehacker/ubuntu:act-20.04"
  ubuntu-18.04: "ghcr.io/catthehacker/ubuntu:act-18.04"
```

### データフロー

1. **ワークフロー読み込み**
   ```
   .github/workflows/*.yml → YAML Parser → AST生成
   ```

2. **実行プラン作成**
   ```
   AST → Dependency Resolver → Execution Plan
   ```

3. **コンテナ実行**
   ```
   Execution Plan → Container Manager → Docker API → Runner Containers
   ```

4. **結果集約**
   ```
   Container Logs → Result Aggregator → Report Generator
   ```

## API設計

### REST API エンドポイント

```yaml
# ワークフロー実行
POST /api/v1/simulate
Content-Type: application/json
{
  "workflow_path": ".github/workflows/ci.yml",
  "event": "push",
  "ref": "refs/heads/main",
  "actor": "testuser",
  "environment": {
    "GITHUB_TOKEN": "***",
    "CUSTOM_VAR": "value"
  }
}

# 実行状況確認
GET /api/v1/simulate/{run_id}
Response:
{
  "id": "run_123",
  "status": "running",
  "jobs": [
    {
      "id": "lint",
      "status": "completed",
      "conclusion": "success",
      "started_at": "2025-01-15T10:00:00Z",
      "completed_at": "2025-01-15T10:05:00Z"
    }
  ]
}

# 実行ログ取得
GET /api/v1/simulate/{run_id}/logs
GET /api/v1/simulate/{run_id}/jobs/{job_id}/logs

# 実行停止
POST /api/v1/simulate/{run_id}/cancel
```

### CLI インターface

```bash
# 基本実行
mcp-docker simulate .github/workflows/ci.yml

# イベント指定実行
mcp-docker simulate .github/workflows/ci.yml --event pull_request

# 環境変数指定
mcp-docker simulate .github/workflows/ci.yml --env-file .env.local

# デバッグモード
mcp-docker simulate .github/workflows/ci.yml --debug --verbose

# 特定ジョブのみ実行
mcp-docker simulate .github/workflows/ci.yml --job build

# レポート出力
mcp-docker simulate .github/workflows/ci.yml --output-format html --output-file report.html
```

## 実装計画

### Phase 1: Core Infrastructure (2週間)
- [ ] YAML Parser実装
- [ ] Basic Job Orchestrator
- [ ] Docker Container Manager
- [ ] CLI基盤構築

### Phase 2: Advanced Features (3週間)
- [ ] マトリックス戦略サポート
- [ ] 環境変数・シークレット管理
- [ ] 実行結果レポーティング
- [ ] エラーハンドリング強化

### Phase 3: Integration & Polish (2週間)
- [ ] 既存MCPサービスとの統合
- [ ] Web UI開発（Optional）
- [ ] パフォーマンス最適化
- [ ] ドキュメント整備

## セキュリティ考慮

### コンテナセキュリティ
- **隔離**: ランナーコンテナは独立したネットワークで実行
- **権限制限**: 非rootユーザーでの実行、最小権限原則
- **リソース制限**: CPU、メモリ、ディスク容量の制限
- **イメージ検証**: 使用するDockerイメージの署名検証

### シークレット管理
- **暗号化**: ローカルシークレットファイルの暗号化保存
- **アクセス制御**: シークレットアクセスの監査ログ
- **マスキング**: ログ出力でのシークレット自動マスキング

## パフォーマンス要件

### 実行時間目標
- **小規模ワークフロー** (1-3 jobs): < 2分
- **中規模ワークフロー** (4-8 jobs): < 5分
- **大規模ワークフロー** (9+ jobs): < 10分

### リソース使用量
- **メモリ使用量**: ホスト物理メモリの70%以下
- **CPU使用量**: 並列実行時でもシステム応答性を維持
- **ディスク使用量**: 一時ファイル、ログの自動クリーンアップ

## モニタリング・ロギング

### 実行メトリクス
- ジョブ実行時間
- リソース使用量（CPU、メモリ、ネットワーク）
- 成功/失敗率
- エラーパターン分析

### ログ管理
- 構造化ログ（JSON形式）
- ログレベル制御（DEBUG、INFO、WARN、ERROR）
- 長期保存とローテーション設定
- 実行コンテキスト情報の保存

## 互換性・制限事項

### 制限事項
1. **GitHub固有サービス**: GitHub Container Registry、GitHub Packages等は利用不可
2. **外部サービス**: 実際のGitHub API呼び出しは制限される場合がある
3. **ハードウェア依存**: macOS/Windows runnerは対応予定なし（Linux Dockerのみ）
4. **ネットワーク制限**: 内部ネットワークアクセスに制限

### 既存ツールとの差別化
- **Act**: より高速で軽量、既存MCPインフラ統合
- **GitHub CLI**: オフライン実行可能、詳細デバッグ情報
- **Nektos/act**: リソース効率性向上、リアルタイム監視

## 今後の拡張予定

### v1.1: Enhanced Runner Support
- Windows Serverコンテナサポート（WSL2環境）
- カスタムランナーイメージ作成支援
- GPUアクセレーション対応

### v1.2: Advanced Integration
- IDE統合（VS Code Extension）
- Git hooks統合による自動実行
- 継続的インテグレーション統計ダッシュボード

### v1.3: Enterprise Features
- 複数プロジェクト管理
- チーム権限管理
- 実行履歴の検索・分析
- Slack/Teams通知統合

## 結論

このGitHub Actions Docker Simulatorは、開発チームの生産性向上とCI/CDパイプラインの信頼性向上に大きく貢献すると期待されます。既存のMcp-Dockerプロジェクトとの統合により、統一されたコンテナベース開発環境を提供し、ローカル開発からプロダクション環境まで一貫した体験を実現します。
