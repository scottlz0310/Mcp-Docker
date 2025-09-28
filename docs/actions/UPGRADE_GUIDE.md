# 🔄 GitHub Actions Simulator - アップグレードガイド

## 📋 概要

GitHub Actions Simulatorの新しいバージョンへのアップグレード手順と、バージョン間の変更点について説明します。

## 🚀 クイックアップグレード

### 自動アップグレード（推奨）

```bash
# 最新バージョンを確認
make version

# 自動アップグレード実行
./scripts/upgrade.sh

# または手動でGitプル
git pull origin main
make build
```

### 手動アップグレード

```bash
# 1. 現在のバージョンを確認
make version

# 2. 最新のコードを取得
git fetch origin
git checkout main
git pull origin main

# 3. 依存関係を更新
uv sync

# 4. Docker環境を再構築
make clean
make build

# 5. 動作確認
make test
./scripts/run-actions.sh --check-deps
```

## 📊 バージョン互換性マトリクス

| バージョン | Python | Docker | act | 互換性 | 推奨アップグレード |
|-----------|--------|--------|-----|--------|-------------------|
| v1.1.x | 3.13+ | 20.10+ | 0.2.40+ | ✅ 完全 | 自動 |
| v1.0.x | 3.12+ | 20.10+ | 0.2.35+ | ⚠️ 部分的 | 手動推奨 |
| v0.x.x | 3.11+ | 19.03+ | 0.2.30+ | ❌ 非対応 | 必須 |

## 🔄 バージョン別アップグレード手順

### v1.0.x → v1.1.x

**主な変更点:**
- 完全自動化リリースシステム導入
- ドキュメント自動生成機能
- 包括的なプラットフォームサポート
- 強化されたテンプレート検証

**アップグレード手順:**

```bash
# 1. バックアップ作成（推奨）
cp -r .env .env.backup 2>/dev/null || true
cp -r docker-compose.override.yml docker-compose.override.yml.backup 2>/dev/null || true

# 2. 最新コードを取得
git pull origin main

# 3. 新しいテンプレートを適用
cp .env.example .env  # 必要に応じて設定を調整
cp .pre-commit-config.yaml.sample .pre-commit-config.yaml

# 4. 環境を再構築
make clean
make build

# 5. 新機能の確認
./scripts/run-actions.sh --check-deps-extended
make test-template-validation
```

**設定ファイルの変更:**
- `.env.example`: 新しい環境変数が追加されました
- `.pre-commit-config.yaml`: GitHub Actions Simulator統合が追加されました
- `docker-compose.override.yml.sample`: 新しいカスタマイズオプションが追加されました

### v0.x.x → v1.1.x（メジャーアップグレード）

**重要な変更:**
- アーキテクチャの軽量化（actベース）
- 新しいCLIインターフェース
- 設定ファイル構造の変更

**アップグレード手順:**

```bash
# 1. 完全バックアップ
tar -czf backup-$(date +%Y%m%d).tar.gz .env* docker-compose.override.yml* 2>/dev/null || true

# 2. クリーンインストール
git checkout main
git pull origin main
make clean-all

# 3. 新しい設定ファイルを作成
cp .env.example .env
# .envファイルを編集して必要な設定を追加

# 4. 環境を構築
make setup
make build

# 5. 移行確認
./scripts/run-actions.sh --check-deps
make test
```

## 🛠️ トラブルシューティング

### よくあるアップグレード問題

#### 1. Docker イメージの競合

```bash
# 症状: 古いイメージが残っている
# 解決方法:
make clean-all
docker system prune -f
make build
```

#### 2. 依存関係の不整合

```bash
# 症状: uv sync でエラーが発生
# 解決方法:
rm -rf .venv
uv sync --reinstall
```

#### 3. 設定ファイルの互換性問題

```bash
# 症状: 古い設定ファイルでエラーが発生
# 解決方法:
mv .env .env.old
cp .env.example .env
# .env.oldから必要な設定をコピー
```

#### 4. pre-commit フックの問題

```bash
# 症状: pre-commit実行でエラー
# 解決方法:
pre-commit uninstall
cp .pre-commit-config.yaml.sample .pre-commit-config.yaml
pre-commit install
pre-commit run --all-files
```

### アップグレード失敗時の復旧

```bash
# 1. バックアップから復旧
git checkout HEAD~1  # 前のコミットに戻る
cp .env.backup .env 2>/dev/null || true

# 2. 環境を再構築
make clean
make build

# 3. 動作確認
make test
```

## 📋 アップグレード前チェックリスト

### 事前準備

- [ ] 現在のバージョンを確認: `make version`
- [ ] 重要な設定ファイルをバックアップ
- [ ] 実行中のプロセスを停止: `make stop`
- [ ] ディスク容量を確認: `df -h`

### アップグレード実行

- [ ] 最新コードを取得: `git pull origin main`
- [ ] 依存関係を更新: `uv sync`
- [ ] Docker環境を再構築: `make build`
- [ ] 設定ファイルを更新

### 事後確認

- [ ] バージョンを確認: `make version`
- [ ] 依存関係チェック: `./scripts/run-actions.sh --check-deps`
- [ ] 基本機能テスト: `make test`
- [ ] 実際のワークフロー実行テスト

## 🔄 自動アップグレードスクリプト

プロジェクトには自動アップグレードスクリプトが含まれています：

```bash
# 自動アップグレード実行
./scripts/upgrade.sh

# オプション付き実行
./scripts/upgrade.sh --backup --test
```

**スクリプトの機能:**
- 自動バックアップ作成
- バージョン互換性チェック
- 段階的アップグレード実行
- 自動テスト実行
- 失敗時の自動復旧

## 📞 サポート

### アップグレードで問題が発生した場合

1. **GitHub Issues**: [問題を報告](https://github.com/scottlz0310/mcp-docker/issues)
2. **診断情報の収集**: `./scripts/run-actions.sh --check-deps > upgrade_issue.txt`
3. **ログの確認**: `make logs > upgrade_logs.txt`

### 緊急時の連絡先

- **GitHub Issues**: バグ報告・機能要望
- **GitHub Discussions**: 質問・アイデア共有
- **ドキュメント**: [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## 📈 リリース通知

新しいバージョンのリリース情報を受け取る方法：

1. **GitHub Watch**: リポジトリをWatchしてリリース通知を受信
2. **RSS Feed**: GitHub ReleasesのRSSフィードを購読
3. **CHANGELOG**: [CHANGELOG.md](../CHANGELOG.md)を定期的に確認

## 🔮 今後のリリース予定

| バージョン | 予定日 | 主な機能 | 互換性 |
|-----------|--------|----------|--------|
| v1.2.0 | 2025年10月 | パフォーマンス最適化 | 後方互換 |
| v1.3.0 | 2025年11月 | 新しいプラットフォーム対応 | 後方互換 |
| v2.0.0 | 2025年12月 | アーキテクチャ刷新 | 破壊的変更 |

---

**GitHub Actions Simulator** - 常に最新の機能をお楽しみください 🚀
