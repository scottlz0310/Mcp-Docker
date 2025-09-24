# MCP Docker Environment - リポジトリ化計画

## Phase 1: リポジトリ設計・初期設定

### 1.1 リポジトリ構成設計
- **目的**: MCP統合Docker環境の管理・配布
- **対象**: GitHub/DateTime/CodeQL MCPサービス
- **技術スタック**: Docker, Docker Compose, Shell, YAML

### 1.2 ディレクトリ構造
```
mcp-docker/
├── .github/workflows/     # CI/CD設定
├── .amazonq/rules/        # 開発ルール
├── services/              # サービス別設定
├── scripts/               # 管理スクリプト
├── docs/                  # ドキュメント
├── tests/                 # 統合テスト
├── Dockerfile             # 統合イメージ
├── docker-compose.yml     # サービス定義
├── Makefile              # 開発コマンド
├── .gitignore            # Git除外設定
├── .env.template         # 環境変数テンプレート
└── README.md             # プロジェクト説明
```

### 1.3 初期タスク
- [x] GitHubリポジトリ作成
- [x] 基本ファイル整備（.gitignore, LICENSE, CONTRIBUTING.md）
- [x] Docker特化ルール策定
- [x] CI/CD設計

### 1.4 Exit Criteria
- [x] リポジトリ作成完了
- [x] 基本構造確立
- [x] 開発ルール合意

## Phase 2: Docker環境実装・CI/CD構築

### 2.1 Docker設定最適化
- [x] 統合Dockerfileの改善
- [x] マルチステージビルド導入
- [x] セキュリティ強化（rootless実行）

### 2.2 CI/CD実装
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  docker-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker build -t mcp-docker .
      - name: Test services
        run: make test
```

### 2.3 品質チェック
- [x] Dockerfile linting (hadolint)
- [x] YAML validation
- [x] Shell script checking (shellcheck)
- [x] セキュリティスキャン (Trivy)

### 2.4 Exit Criteria
- [x] Docker build成功
- [x] 全サービス起動確認
- [x] CI/CD動作確認

## Phase 3: テスト・ドキュメント整備

### 3.1 統合テスト実装
- [x] 基本統合テスト作成
- [x] Docker buildテスト
- [x] サービス起動テスト
- [x] DateTime Validator動作テスト
- [x] コンテナヘルスチェック

### 3.2 ドキュメント整備
- [x] README.md詳細化
- [x] CONTRIBUTING.md作成
- [x] API仕様書
- [x] トラブルシューティングガイド

### 3.3 Exit Criteria
- [x] 統合テスト完成
- [x] ドキュメント完備
- [x] 使用方法明確化

## Docker特化開発ルール

### コンテナ設計原則
- **単一責任**: 1コンテナ1サービス
- **軽量化**: Alpine Linux使用、不要パッケージ削除
- **セキュリティ**: 非rootユーザー実行、最小権限

### 設定管理
- 環境変数による設定注入
- シークレット管理（Docker secrets/環境変数）
- 設定ファイルのボリュームマウント

### テスト戦略
- **ビルドテスト**: Dockerfile構文・依存関係
- **起動テスト**: サービス正常起動確認
- **統合テスト**: サービス間連携確認
- **セキュリティテスト**: 脆弱性スキャン

### CI/CD要件
- **プラットフォーム**: Ubuntu Linuxのみ（現実的な範囲）
- **キャッシュ**: Docker layer caching
- **セキュリティ**: Trivyスキャン（CRITICAL/HIGHのみ）
- **リリース**: タグ付きイメージ自動push

## 進捗管理

### マイルストーン
1. **Week 1**: リポジトリ作成・基本構造
2. **Week 2**: CI/CD構築・Docker最適化
3. **Week 3**: テスト実装・ドキュメント整備
4. **Week 4**: リリース準備・品質確認

### 優先度
- **High**: リポジトリ作成、CI/CD、セキュリティ
- **Medium**: テスト自動化、ドキュメント
- **Low**: 高度な機能、パフォーマンス最適化

## リスク・対策

### 技術リスク
- **Docker互換性**: 複数バージョンでのテスト
- **セキュリティ**: 定期的な脆弱性スキャン
- **依存関係**: ベースイメージ更新戦略

### 運用リスク
- **設定管理**: 環境変数の標準化
- **トラブルシューティング**: ログ集約・監視
- **バックアップ**: 設定・データの保護

## Phase 4: リンティング・コード品質

### 4.1 リンター・フォーマッター・検証
- [x] hadolint（Dockerfile lint）実装
- [x] shellcheck（Shell script）実装
- [x] yamllint（YAML）実装
- [x] pre-commit設定完了

### 4.2 スタイルガイド
- [x] Dockerfile: 公式ベストプラクティス準拠
- [x] Shell: POSIX準拠、shellcheck対応
- [x] YAML: 2スペースインデント、yamllint設定

### 4.3 セキュリティ静的解析
- [x] Trivy（コンテナ脆弱性）CI統合
- [x] GitHub CodeQL設定（SARIF出力）
- [x] セキュリティスキャン自動化

### 4.4 Exit Criteria
- [x] 全リンター動作確認
- [x] セキュリティスキャン統合
- [x] 品質ゲート設定完了

## Phase 5: テスト戦略・カバレッジ

### 5.1 テストフレームワーク
- [x] Bats（Bash testing）導入
- [x] 統合テストスクリプト実装
- [x] Docker test containers対応

### 5.2 テスト種別実装
- [x] Docker buildテスト（test_docker_build.bats）
- [x] サービス起動テスト（test_services.bats）
- [x] セキュリティテスト（test_security.bats）
- [x] 統合テスト（test_integration.bats）
- [x] CI環境対応（権限問題回避）

### 5.3 テスト自動化
- [x] Makefile統合（test-all, test-docker等）
- [x] CI/CDパイプライン統合
- [x] マトリクステスト（OS × Dockerバージョン）

### 5.4 Exit Criteria
- [x] 全テスト種別実装完了
- [x] CI/CD統合完了
- [x] テストカバレッジ確保

## Phase 6: CI/CD・自動化

### 6.1 CI/CDパイプライン
- [x] GitHub Actions設定（ci.yml）
- [x] Linuxフォーカス設計（Ubuntuのみ）
- [x] Docker layer caching実装
- [x] 権限最小化（permissions設定）

### 6.2 リリース自動化
- [x] 🚀 Release Management ワークフロー（release.yml）
- [x] 2つのトリガー（workflow_dispatch・push tags）
- [x] 5段階ジョブ構成（version-check → quality-check → prepare-release → create-release → post-release）
- [x] スマートバージョンチェック（pyproject.toml + main.py同期更新）
- [x] Conventional Commits解析によるCHANGELOG自動生成
- [x] カテゴリ別変更内容分類（✨新機能・🐛修正・📝ドキュメント・🔧その他）
- [x] 重複回避機能（既存エントリは日付のみ更新）
- [x] GitHub Release自動作成（アセット添付）
- [x] バージョン後退禁止（セキュリティ機能）
- [x] 条件付きタグ作成（手動実行時のみ）

### 6.3 品質ゲート・保護設定
- [x] ブランチ保護設定スクリプト
- [x] CODEOWNERS設定
- [x] 必須チェック設定
- [x] レビュー体制確立

### 6.4 Exit Criteria
- [x] 完全自動化リリースフロー確立
- [x] マトリクステスト動作確認
- [x] ブランチ保護・レビュー体制確立

---

## Phase 7: セキュリティ・品質保証（リカバリー中）

### 7.1 GitHub Advanced Security
- [x] GitHub Advanced Security有効化（security.ymlワークフロー）
- [x] Dependabot設定拡張（dependabot.yml）
- [x] Secret scanning設定（TruffleHog統合）
- [x] Code scanning設定（CodeQL + Trivy SARIF出力）

### 7.2 依存関係監査・SBOM
- [x] SBOM生成スクリプト（scripts/generate-sbom.py）
- [x] 依存関係監査自動化（scripts/audit-dependencies.py）
- [x] ライセンス監査（security.ymlワークフロー統合）

### 7.3 不足実装補完
- [x] バージョン管理スクリプト（scripts/version-manager.py）
- [x] GitHub MCP Serverサービス復活
- [x] サービス設定ディレクトリ整備
- [x] ドキュメント拡充（セキュリティワークフロー・SBOM・監査）

### 7.4 Exit Criteria
- [x] 全セキュリティ機能有効化
- [x] 不足実装完全補完
- [x] ドキュメント完備

---

**現在の状況**: Phase 7 完了（2025-09-24 17:30 UTC）
**リカバリー作業完了、全機能実装済み**

**実装完了項目**:
- ✅ 🚀 Release Management完全自動化ワークフロー
  - 手動実行（workflow_dispatch）・タグプッシュ（push tags）対応
  - 5段階ジョブ構成による段階的処理
  - スマートバージョンチェック（後退禁止・自動更新）
  - Conventional Commits解析CHANGELOG生成
  - カテゴリ別変更分類・重複回避機能
  - GitHub Release自動作成・アセット添付
- ✅ LinuxフォーカスCI（Ubuntuのみ、現実的な範囲）
- ✅ ブランチ保護設定自動化（setup-branch-protection.sh）
- ✅ CODEOWNERS設定（全ファイル@scottlz0310）
- ✅ Batsテストスイート（4種類：build/services/security/integration）
- ✅ セキュリティスキャン（Trivy + CodeQL + SARIF出力）
- ✅ 品質チェック（hadolint, shellcheck, yamllint, pre-commit）
- ✅ Docker最適化（マルチステージビルド、rootless実行、Alpine Linux）

**Phase 7で復旧完了した実装項目**:
- ✅ バージョン管理スクリプト（scripts/version-manager.py）
- ✅ GitHub MCP Serverサービス統合（docker-compose.yml復活）
- ✅ services/github/設定ディレクトリ
- ✅ services/codeql/設定ディレクトリ
- ✅ GitHub Advanced Security設定（.github/workflows/security.yml）
- ✅ SBOM生成・依存関係監査（scripts/generate-sbom.py, audit-dependencies.py）
- ✅ ドキュメント拡充復旧

**リカバリー完了**: 全Phase 7実装復旧 (2025-09-24)
1. ✅ **優先度High**: バージョン管理スクリプト復旧
2. ✅ **優先度High**: GitHub MCP Serverサービス復旧
3. ✅ **優先度Medium**: サービス設定ディレクトリ復旧
4. ✅ **優先度Medium**: GitHub Advanced Security復旧
5. ✅ **優先度Low**: ドキュメント拡充復旧

**リカバリー戦略**: 段階的復旧でCI安定性を保持 → 完了

**リリースワークフロー状況**: 完全実装済み(2025-09-24)
- 🎯 2つのリリース方法（手動実行推奨・タグプッシュ）
- 🤖 完全自動化（ワンクリック→GitHub Release作成）
- 🛡️ セキュリティ機能（バージョン後退禁止・権限最小化）
- 📝 自動ドキュメント生成（CHANGELOG・リリースノート）
- 🔄 Git履歴ベース（Conventional Commits解析）
