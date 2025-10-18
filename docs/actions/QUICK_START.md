# GitHub Actions Simulator - クイックスタート

## 🚀 5分で始めるGitHub Actions Simulator

### ステップ1: 前提条件の確認（1分）

```bash
# 必要なツールの確認
docker --version    # Docker 20.10+
python --version    # Python 3.13+
git --version       # Git 2.30+
```

### ステップ2: セットアップ（2分）

```bash
# リポジトリのクローン
git clone https://github.com/scottlz0310/mcp-docker.git
cd mcp-docker

# 環境設定
cp .env.example .env
# .envファイルを編集してGitHubトークンを設定

# 依存関係のインストール
uv sync
```

### ステップ3: 初回実行（2分）

```bash
# 自動実行（最も簡単）
make actions-auto

# または対話モード
make actions

# または直接実行
./scripts/run-actions.sh .github/workflows/ci.yml
```

## 🎯 基本的な使用パターン

### パターン1: ワンショット実行

```bash
# 特定のワークフローを実行
make actions-run WORKFLOW=.github/workflows/ci.yml

# ジョブを指定して実行
make actions-run WORKFLOW=.github/workflows/ci.yml JOB=test

# 詳細ログ付きで実行
make actions-run WORKFLOW=.github/workflows/ci.yml VERBOSE=1
```

> Note: `make actions-run` は Phase1 の `act` ブリッジを既定で有効化します。ブリッジが未対応の機能は自動でレガシー実装にフォールバックし、警告を表示します。

### パターン2: 対話モード

```bash
# 対話的にワークフローを選択
make actions

# 利用可能なワークフローを一覧表示
make actions-list
```

### パターン3: 診断・デバッグ

```bash
# 依存関係チェック
./scripts/run-actions.sh --check-deps

# ヘルスチェック
make health-check

# デバッグモード
make actions-debug
```

## 🔧 よく使うコマンド

### 開発・テスト

```bash
# 統合テスト
make test

# セキュリティスキャン
make security

# ドキュメント整合性チェック
make check-docs
```

### 保守・管理

```bash
# Docker環境のクリーンアップ
make clean

# バージョン確認
make version

# 設定の検証
make validate-security
```

## 📋 実用的な使用例

### CI/CDワークフローのテスト

```bash
# CIワークフローの実行
make actions-run WORKFLOW=.github/workflows/ci.yml

# セキュリティスキャンワークフローの実行
make actions-run WORKFLOW=.github/workflows/security.yml

# リリースワークフローの実行
make actions-run WORKFLOW=.github/workflows/release.yml
```

### トラブルシューティング

```bash
# 診断情報の収集
./scripts/run-actions.sh --diagnose

# ハングアップ問題の検出
make test-hangup

# Docker環境の確認
make docker-health
```

### 高度な機能

```bash
# 非対話モードでの自動化
NON_INTERACTIVE=1 ./scripts/run-actions.sh .github/workflows/ci.yml

# カスタム環境変数での実行
ENV_VARS="NODE_ENV=test,DEBUG=1" make actions-run WORKFLOW=.github/workflows/test.yml

# ドライランモード
make actions-dry-run WORKFLOW=.github/workflows/ci.yml
```

## 🆘 困ったときは

### エラーが発生した場合

1. **依存関係チェック**: `./scripts/run-actions.sh --check-deps`
2. **ヘルスチェック**: `make health-check`
3. **ログ確認**: `make logs`
4. **トラブルシューティング**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### さらに詳しく知りたい場合

- [ユーザーガイド](USER_GUIDE.md) - 詳細な使用方法
- [CLIリファレンス](CLI_REFERENCE.md) - 全コマンドリファレンス
- [FAQ](FAQ.md) - よくある質問と回答
- [プラットフォーム対応](PLATFORM_SUPPORT.md) - OS別の対応状況

## 🎉 次のステップ

クイックスタートが完了したら、以下を試してみてください：

1. **カスタムワークフローの作成**
2. **CI/CD統合の設定**
3. **高度な診断機能の活用**
4. **パフォーマンス監視の設定**
