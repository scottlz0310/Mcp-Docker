# 統合テスト（Integration Tests）

## 目的

このディレクトリには、**複数コンポーネントの連携や外部システムとの統合を検証するテスト**を配置します。

## 対象

- Docker操作を含むテスト
- ファイルI/O、データベースアクセスを含むテスト
- 複数サービス間の連携テスト
- 外部APIとの統合テスト

## テストファイル例

### Pytestテスト

- `test_docker_integration_checker.py` - Docker統合チェック
- `test_actions_service.py` - GitHub Actions サービス統合
- `test_diagnostic_service.py` - 診断サービス統合
- `test_auto_recovery.py` - 自動リカバリ機能統合

### Batsテスト

- `test_docker_build.bats` - Dockerビルドテスト
- `test_services.bats` - サービス起動・停止テスト
- `test_integration.bats` - 一般統合テスト
- `test_security.bats` - セキュリティチェック
- `test_actions_simulator.bats` - Actions シミュレーター統合

## 実行方法

```bash
# 統合テストのみ実行
make test-integration

# Pytestのみ
pytest tests/integration/ -v

# Batsのみ
bats tests/integration/*.bats
```

## ガイドライン

### ✅ 統合テストに適している

- Docker コンテナの起動・停止
- サービス間のAPI通信
- ファイル読み書き
- データベース操作
- 設定ファイルの検証

### ❌ 統合テストに適していない

- 純粋なロジックテスト → `unit/`へ
- 完全なユーザーシナリオ → `e2e/`へ

## テスト作成のベストプラクティス

1. **適切なセットアップ/クリーンアップ**: `setUp()`/`tearDown()`やfixture
で環境を準備・後片付け
2. **テストの独立性**: 各テストは独立して実行可能
3. **リソース管理**: Docker コンテナ等は必ずクリーンアップ
4. **実行時間**: 可能な限り高速化（< 10秒/テストを目標）
5. **retry機能**: 外部依存による一時的失敗に対応
6. **明確なアサーション**: 何を検証しているか明確に

## Batsテストの注意事項

- `test_helper.bash`を活用して共通処理を共有
- `@test`ディレクティブで各テストケースを定義
- `setup()`/`teardown()`で前処理・後処理を実装
- Docker操作は必ず`docker-compose down`でクリーンアップ
