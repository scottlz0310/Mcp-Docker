# Docker特化品質ルール

## Phase 4: リンティング・コード品質

### 4.1 リンター・フォーマッター・検証
標準ツール:
- hadolint（Dockerfile lint）, shellcheck（Shell script）, yamllint（YAML）

基本コマンド:
```bash
hadolint Dockerfile
shellcheck scripts/*.sh
yamllint docker-compose.yml
```

補足:
- Dockerfileのベストプラクティス準拠
- Shell scriptのPOSIX互換性確保
- YAML構文とDocker Compose仕様準拠

### 4.2 スタイルガイド
- Dockerfile: 公式ベストプラクティス準拠
- Shell: POSIX準拠、bash固有機能は明示的に宣言
- YAML: 2スペースインデント、一貫したキー順序

### 4.3 セキュリティ静的解析
- 開発中スキャン: Amazon Q Developerセキュリティースキャン等
- 補助: Trivy（コンテナ脆弱性）、Grype（依存関係）を導入

### 4.4 デバッグ・ログ
- echo使用は最小限。構造化ログを推奨
- 構造化ログ（JSON）を標準とする
- ログレベルの運用: DEBUG/INFO/WARNING/ERRORを適切に使用

### 4.5 推奨hadolintルール（例）
- DL3008: パッケージバージョン固定
- DL3009: apt-get clean実行
- DL3015: yum clean実行
- DL4006: SHELL使用推奨

### 4.6 推奨shellcheckルール（例）
```
# .shellcheckrc
disable=SC2034  # 未使用変数（設定ファイルで許可）
enable=all
```

## Phase 5: テスト戦略・カバレッジ

### 5.1 構成
- フレームワーク: Bats（Bash testing）, Docker test containers
- 配置: tests/ディレクトリ配下、ファイル名はtest_*.bats
- 統合テストによるサービス動作確認

### 5.2 テスト目標
- 最終目標: 全サービス起動確認（production）
- CIで動作確認を設定し、失敗はブロック
- テスト設定は段階的厳格化がしやすいようにMakefileで一元管理する

### 5.3 段階別方針
```
prototype:
  - ビルドテスト中心、起動確認のみ
staging:
  - 統合テスト追加、サービス間連携確認
production:
  - E2E/パフォーマンス、セキュリティテスト必須
```

### 5.4 絶対ルール

禁止:
- テスト成功を目的とする条件緩和・簡素化
- テスト失敗を回避する目的のskip
- 動作確認稼ぎのみを目的としたテスト
  - サービス起動だけでヘルスチェックなし
  - 固定レスポンスのみの確認
  - 既存テストと同一の確認項目
- 無意味なコンテナ起動/停止の繰り返し

必須:
- 各テストは以下のいずれかを含むこと
  - サービス起動とヘルスチェック
  - API応答の正常性確認
  - ログ出力の妥当性確認
- 新規テスト作成は例外的な場合のみ
  - 既存テストが肥大化する場合
  - 新しいサービスや設定パターンを扱う場合
- 各テストには目的をコメントで明記
  - 例: # 検証対象: GitHub MCP # 目的: API接続確認
- テストレポート（docker-compose logs）を必ず確認し、エラーログを特定して重点的にテストを追加すること

### 5.5 テストデータと再現性
- 環境変数の固定注入。時刻依存は固定注入（UTC）
- タイムゾーンは常にUTC。I/Oは安定化（並び順・ロケール固定）
- テストデータは一時的なボリューム使用

### 5.6 統合/E2E/パフォーマンス
- 外部APIは契約テストまたは信頼できるスタブで検証
- サービス間通信は実体で統合テスト
- パフォーマンスの基準値を設定し、回帰を検出

### 5.7 Mock戦略
- 各プラットフォーム(Windows,Linux,macOS)依存のテストは実環境を優先して、Mockによる代替は行わない
- 実環境に合わないテストはSKIP処理を用いて適切に除外する
- Mockの使用は最小限とするが、以下のケースでは適切にMockを使用する
 - 外部依存に関係する部分
 - 破壊的変更が起こるケース
 - 非決定的挙動を含む処理
 - エッジケースの再現が必要な場合

## Phase 6: CI/CD・自動化

### 6.1 マトリクス・キャッシュ
- OS × Dockerバージョンのマトリクス（Ubuntu/Windows/macOS × Docker 20.10/24.0目安）
- キャッシュキーはDockerfile、docker-compose.yml、依存関係を含める

### 6.2 必須チェック
- Docker build成功
- hadolint（Dockerfile）、shellcheck（Shell）、yamllint（YAML）
- セキュリティスキャン（Trivy/Grype/Secret scan）
- 統合テスト（全サービス起動確認）

### 6.3 デプロイ・環境保護
- 環境別に承認ゲートを設定（stg→prod）
- Branch Protection: 必須チェック、force-push禁止、linear history、必須レビュー人数を設定

### 6.4 失敗時通知
- Slack/Teams/GitHub通知を自動化。MTTA/MTTRの短縮を図る

### 6.5 Pre-commit規約
- 自動修正時はgit commit --amend --no-editを使用し、元メッセージは変更しない
- 自動修正のみ: "fix: pre-commitによる自動修正"

### 6.6 コミット規約・バージョニング
- Conventional Commits（feat, fix, docs, refactor, test, chore, perf, build, ci）
- SemVer準拠。重大変更はPR/CHANGELOGで明示

### 6.7 署名・DCO
- 署名コミット（GPG/SSH）またはDCOの採用を推奨。プロジェクトで統一

### 6.8 リリース
- タグ付与・GitHub Releaseの自動ノート生成
- Dockerイメージの自動push（Docker Hub/GHCR）
- バージョン整合（docker-compose.yml / CHANGELOG / タグ）をCIで検証

### 6.9 CIワークフロー項目（参考）
- トリガ: PR, push（main）, schedule
- ジョブ: setup → build → lint → security → test → push
- マトリクス: os=[ubuntu-latest, windows-latest, macos-latest], docker=[20.10, 24.0]
- permissions: contents: read, packages: write（必要時のみ）等
- キャッシュキー: hashFiles('Dockerfile', 'docker-compose.yml')

## Phase 7: セキュリティ・品質保証

### 7.1 継続的セキュリティチェック
- GitHub Advanced Security（CodeQL, Secret scanning, Dependabot）を有効化
- コンテナスキャン（Trivy, Grype）をCIに組込

### 7.2 依存監査・SBOM・ライセンス
- SBOM生成（CycloneDX等）を定期的に実施
- ライセンス監査: 許容/禁止ライセンス一覧を維持
- ベースイメージの定期更新戦略

### 7.3 秘密情報管理
- ローカル: .env（コミット禁止）。CI: OIDC＋リポジトリ/環境シークレット
- ログ/CI出力のシークレットマスキングを強制

### 7.4 権限最小化
- GitHub Actionsのpermissionsを最小化（read標準、必要時writeを限定）
- トークン権限の最小化・短命化

### 7.5 コンテナセキュリティ
- ベースイメージの定期更新。Trivy等でスキャン
- ルートレス/最小権限実行、不要パッケージ削減
- 非rootユーザーでの実行を強制

### 7.6 セキュリティ例外の承認
- 例外は期限・迂回策・再評価日を文書化し、承認者を明記

## Phase 8: 観測性・監視

### 8.1 構造化ログ
- JSONを標準。必須フィールド: timestamp（UTC, ISO8601）, level, event, message, service, container_id, image_tag
- PIIはマスキング/匿名化。PlainなPII出力は禁止

### 8.2 メトリクス/ヘルスチェック
- Docker Composeヘルスチェック設定必須
- サービス固有のヘルスエンドポイント実装

### 8.3 時刻・日付記録規則
- 全ログはtimezone-aware UTCを使用する
- ドキュメント上の日時は原則CI/ビルド時に自動埋め込みする
- やむを得ず手入力で日時を記載する場合は、dateコマンド等で実際の現在時刻を確認してから記載すること（UTC/ISO 8601など形式を統一）
  - 例（POSIX）: `date -u +"%Y-%m-%d %H:%M:%S"`
  - 例（PowerShell）: `Get-Date -AsUTC -Format "yyyy-MM-dd HH:mm:ss"`

## Docker特有の品質要件

### イメージ品質・最適化
- マルチステージビルドによるサイズ最適化
- レイヤー数の最小化
- キャッシュ効率の最大化

### セキュリティ・脆弱性管理
- 定期的な脆弱性スキャン
- ベースイメージの更新戦略
- 最小権限の原則

### パフォーマンス・リソース管理
- リソース制限の設定
- 起動時間の最適化
- メモリ使用量の監視

## レビュー体制・品質ゲート

### レビュー体制/CODEOWNERS
- CODEOWNERSで責任範囲を明確化。必須レビュア数を設定
- 設計/実装/品質/セキュリティレビューを各フェーズ終盤に実施

### 品質ゲート
- 各Phaseの完了条件（Exit Criteria）を満たすまで次段階に進まない
- Phase 4: セキュリティレビュー完了、未解決脆弱性0
- Phase 5: デプロイ承認、環境保護設定完了
- Phase 6: 安定運用開始、Runbook整備

---

## 付録

### 付録A. 推奨.gitignore追記（Docker特化）
```
# Docker
.env
.env.*
!.env.template
!.env.example

# Docker volumes
volumes/
data/

# Build artifacts
*.tar
*.tar.gz

# Logs
logs/
*.log

# OS generated files
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
```

### 付録B. 推奨Makefileターゲット例
```Makefile
.PHONY: setup build start stop logs test clean security
setup:
	cp .env.template .env
	docker network create mcp-network || true

build:
	docker-compose build

start:
	docker-compose up -d

stop:
	docker-compose down

logs:
	docker-compose logs -f

test:
	./tests/integration_test.sh

security:
	trivy image mcp-docker:latest

clean:
	docker-compose down -v
	docker system prune -f
```

---
遵守事項:
- 本ルールはプロジェクトの品質基盤であり、逸脱はレビュー承認が必要である
- 品質要件は段階的に厳格化し、最終的にproduction品質を達成すること
