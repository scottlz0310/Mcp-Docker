# GitHub Actions Simulator - よくある質問（FAQ）

## 📋 目次

- [🚀 基本的な質問](#-基本的な質問)
- [⚙️ インストール・セットアップ](#️-インストールセットアップ)
- [🎛️ 使用方法](#️-使用方法)
- [🔧 トラブルシューティング](#-トラブルシューティング)
- [🛠️ 開発・カスタマイズ](#️-開発カスタマイズ)
- [🚀 CI/CD統合](#-cicd統合)
- [🔒 セキュリティ](#-セキュリティ)
- [📊 パフォーマンス](#-パフォーマンス)

## 🚀 基本的な質問

### Q: GitHub Actions Simulatorとは何ですか？

**A:** GitHub Actions Simulatorは、軽量で使いやすいローカルワークフローシミュレーターです。Docker + actベースの軽量アーキテクチャにより、複雑な設定なしに5分でGitHub Actionsワークフローの事前チェックが可能です。

**主な特徴:**
- ⚡ 高速起動（数秒でワークフロー実行開始）
- 🪶 軽量（Docker + actのみでフル機能）
- 🔧 簡単（ワンコマンドでの実行）
- 🛡️ 安全（コンテナ内での隔離実行）

### Q: なぜローカルでGitHub Actionsをシミュレートする必要があるのですか？

**A:** ローカルシミュレーションには以下のメリットがあります：

- **⚡ 高速フィードバック**: GitHubにプッシュする前にエラーを発見
- **💰 コスト削減**: GitHub Actionsの実行時間を節約
- **🔄 反復開発**: 素早い修正とテストの繰り返し
- **🛡️ セキュリティ**: 本番環境に影響を与えずにテスト
- **📊 品質向上**: 事前チェックによる品質の向上

### Q: 他のローカル実行ツールとの違いは何ですか？

**A:** GitHub Actions Simulatorの独自の特徴：

| 特徴 | GitHub Actions Simulator | 他のツール |
|------|-------------------------|-----------|
| **セットアップ** | ワンコマンドで完了 | 複雑な設定が必要 |
| **依存関係** | Docker + actのみ | 多数の依存関係 |
| **診断機能** | 包括的な自動診断 | 基本的なエラー表示 |
| **自動復旧** | 自動エラー修復 | 手動修正が必要 |
| **監視機能** | リアルタイム監視 | 限定的な監視 |

## ⚙️ インストール・セットアップ

### Q: 必要な前提条件は何ですか？

**A:** 以下の環境が必要です：

**必須:**
- Docker 20.10+ & Docker Compose 2.0+
- Git 2.20+

**推奨:**
- uv（Python パッケージマネージャー）

**確認方法:**
```bash
./scripts/run-actions.sh --check-deps
```

### Q: Dockerがインストールされていない場合はどうすればよいですか？

**A:** プラットフォーム別のインストール方法：

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

**macOS:**
```bash
brew install --cask docker
```

**Windows:**
1. Docker Desktop for Windowsをダウンロード
2. WSL2を有効化
3. Docker Desktopをインストール

**詳細なガイダンス:**
```bash
./scripts/run-actions.sh --check-deps
```

### Q: uvがインストールされていなくても使用できますか？

**A:** はい、uvがなくても動作します。ただし、uvを使用することで以下のメリットがあります：

- **⚡ 高速**: パッケージインストールの高速化
- **🔒 安全**: 依存関係の厳密な管理
- **🎯 効率**: 仮想環境の自動管理

**uvのインストール:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Q: 権限エラーが発生します。どうすればよいですか？

**A:** 権限エラーの解決方法：

**1. Dockerグループへの追加:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

**2. Docker サービスの確認:**
```bash
sudo systemctl status docker
sudo systemctl start docker
```

**3. 権限の確認:**
```bash
docker run hello-world
```

**詳細な診断:**
```bash
./scripts/run-actions.sh --check-deps
```

## 🎛️ 使用方法

### Q: 最も簡単な使い方は何ですか？

**A:** 最もシンプルな使用方法：

```bash
# 対話的選択（初心者向け）
./scripts/run-actions.sh

# 特定ワークフローの直接実行
./scripts/run-actions.sh .github/workflows/ci.yml
```

### Q: 複数のワークフローファイルがある場合はどうすればよいですか？

**A:** 複数の方法があります：

**1. 対話的選択:**
```bash
./scripts/run-actions.sh
# → ワークフローファイルの一覧から選択
```

**2. 特定ファイルの指定:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml
./scripts/run-actions.sh .github/workflows/test.yml
./scripts/run-actions.sh .github/workflows/deploy.yml
```

**3. インデックス指定（自動化向け）:**
```bash
INDEX=1 ./scripts/run-actions.sh  # 1番目のワークフロー
INDEX=2 ./scripts/run-actions.sh  # 2番目のワークフロー
```

### Q: 特定のジョブのみ実行できますか？

**A:** はい、特定のジョブのみ実行可能です：

```bash
# 特定のジョブのみ実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --job test

# 複数のジョブを実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --job test --job lint

# ジョブの一覧表示
./scripts/run-actions.sh .github/workflows/ci.yml -- --list
```

### Q: 環境変数を設定して実行できますか？

**A:** 複数の方法で環境変数を設定できます：

**1. コマンドライン引数:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --env GITHUB_ACTOR=ci-bot --env NODE_ENV=test
```

**2. Makeコマンド:**
```bash
ENV_VARS="NODE_ENV=dev,DEBUG=true" make actions WORKFLOW=.github/workflows/test.yml
```

**3. .envファイル:**
```bash
cp .env.template .env
# .envファイルを編集
./scripts/run-actions.sh .github/workflows/ci.yml
```

### Q: 実行結果をファイルに保存できますか？

**A:** はい、複数の出力形式をサポートしています：

**JSON形式:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --output-format json --output-file output/simulation-report.json
```

**詳細ログ:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --verbose > detailed-log.txt 2>&1
```

**デバッグ情報:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --debug --show-execution-trace > debug-report.txt 2>&1
```

## 🔧 トラブルシューティング

### Q: 「Docker デーモンに接続できません」エラーが発生します

**A:** Docker接続エラーの解決方法：

**1. Docker サービスの状態確認:**
```bash
sudo systemctl status docker
```

**2. Docker サービスの再起動:**
```bash
sudo systemctl restart docker
```

**3. ユーザー権限の確認:**
```bash
groups | grep docker
# dockerグループにいない場合：
sudo usermod -aG docker $USER
newgrp docker
```

**4. 診断機能の使用:**
```bash
./scripts/run-actions.sh --check-deps
```

### Q: ワークフローファイルが見つからないエラーが発生します

**A:** ファイルパスの問題の解決方法：

**1. ファイルの存在確認:**
```bash
ls -la .github/workflows/
```

**2. 対話的選択の使用:**
```bash
./scripts/run-actions.sh
# → 利用可能なワークフローファイルが表示される
```

**3. 絶対パスでの指定:**
```bash
./scripts/run-actions.sh $(pwd)/.github/workflows/ci.yml
```

**4. ワークフローファイルの作成:**
```bash
mkdir -p .github/workflows
# サンプルワークフローファイルをコピー
```

### Q: 実行が途中で停止します

**A:** 実行停止の問題の解決方法：

**1. 自動復旧機能の使用:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- --auto-recovery
```

**2. 強化されたプロセス監視:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- --enhanced
```

**3. タイムアウト設定の調整:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- --timeout 1800
```

**4. 詳細診断の実行:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --diagnose --show-execution-trace --debug
```

### Q: メモリ不足エラーが発生します

**A:** メモリ不足の解決方法：

**1. システムリソースの確認:**
```bash
./scripts/run-actions.sh --check-deps
free -h
df -h
```

**2. 不要なコンテナの削除:**
```bash
docker container prune -f
docker image prune -f
docker system prune -f
```

**3. 特定のジョブのみ実行:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- --job test
```

**4. メモリ制限の調整:**
```bash
# docker-compose.override.ymlでメモリ制限を設定
```

### Q: ワークフローの構文エラーが発生します

**A:** 構文エラーの解決方法：

**1. 構文チェックのみ実行:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- --dry-run
```

**2. YAMLリンターの使用:**
```bash
yamllint .github/workflows/ci.yml
```

**3. 詳細診断の実行:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- --diagnose
```

**4. GitHub Actions構文の確認:**
- [GitHub Actions構文リファレンス](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

## 🛠️ 開発・カスタマイズ

### Q: 開発環境をセットアップするにはどうすればよいですか？

**A:** 開発環境のセットアップ手順：

**1. 依存関係の確認:**
```bash
./scripts/run-actions.sh --check-deps
```

**2. 開発依存関係のインストール:**
```bash
uv sync --group dev
```

**3. Pre-commitフックの設定:**
```bash
pre-commit install
```

**4. 開発用Docker環境の構築:**
```bash
make build
```

### Q: カスタム設定を追加するにはどうすればよいですか？

**A:** カスタム設定の追加方法：

**1. 環境変数ファイルの作成:**
```bash
cp .env.template .env
# .envファイルを編集してカスタム設定を追加
```

**2. Docker設定のカスタマイズ:**
```bash
cp docker-compose.override.yml.sample docker-compose.override.yml
# オーバーライドファイルを編集
```

**3. 設定の確認:**
```bash
./scripts/run-actions.sh --check-deps
```

### Q: 新しい機能を追加するにはどうすればよいですか？

**A:** 機能追加の手順：

**1. フォークとブランチ作成:**
```bash
git checkout -b feature/new-feature
```

**2. 開発とテスト:**
```bash
# 機能を実装
make test
make security
```

**3. プルリクエストの作成:**
- 変更内容の説明
- テスト結果の添付
- ドキュメントの更新

**詳細:** [CONTRIBUTING.md](../../CONTRIBUTING.md)

### Q: デバッグモードで実行するにはどうすればよいですか？

**A:** デバッグモードの使用方法：

**1. 基本的なデバッグ:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- --debug
```

**2. 詳細なトレース:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --debug --show-execution-trace --verbose
```

**3. ログファイルの確認:**
```bash
tail -f logs/error.log
tail -f logs/diagnostic.log
```

## 🚀 CI/CD統合

### Q: GitHub ActionsでGitHub Actions Simulatorを使用できますか？

**A:** はい、GitHub Actionsでの使用例：

```yaml
name: Local CI Simulation
on: [push, pull_request]

jobs:
  simulate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Dependencies
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Run GitHub Actions Simulation
        run: |
          NON_INTERACTIVE=1 ./scripts/run-actions.sh .github/workflows/ci.yml
        env:
          GITHUB_ACTOR: ${{ github.actor }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Q: pre-commitフックで使用できますか？

**A:** はい、pre-commitフックでの使用例：

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: github-actions-simulation
        name: GitHub Actions Simulation
        entry: ./scripts/run-actions.sh
        args: ['.github/workflows/ci.yml', '--', '--job', 'test']
        language: system
        pass_filenames: false
```

### Q: 非対話モードで実行するにはどうすればよいですか？

**A:** 非対話モードの使用方法：

**1. 環境変数での制御:**
```bash
NON_INTERACTIVE=1 ./scripts/run-actions.sh .github/workflows/ci.yml
```

**2. インデックス指定:**
```bash
INDEX=1 ./scripts/run-actions.sh
```

**3. 環境変数の組み合わせ:**
```bash
export NON_INTERACTIVE=1
export WORKFLOW_INDEX=1
./scripts/run-actions.sh
```

### Q: CI/CD環境での失敗時の対処方法は？

**A:** CI/CD環境での失敗対処：

**1. 詳細ログの有効化:**
```bash
NON_INTERACTIVE=1 ./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --debug --show-execution-trace
```

**2. 診断情報の収集:**
```bash
./scripts/run-actions.sh --check-deps > system-info.txt
```

**3. エラーログの保存:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml 2>&1 | tee simulation.log
```

## 🔒 セキュリティ

### Q: セキュリティ上の注意点はありますか？

**A:** セキュリティのベストプラクティス：

**1. 秘密情報の管理:**
```bash
# .envファイルをコミットしない
echo ".env" >> .gitignore

# テンプレートファイルのみコミット
git add .env.template
```

**2. 権限の最小化:**
```bash
# 非root実行の確認
./scripts/run-actions.sh --check-deps | grep -i "root"

# Dockerグループの確認
groups | grep docker
```

**3. 定期的なセキュリティスキャン:**
```bash
make security
make audit-deps
```

### Q: 秘密情報（トークンなど）はどう扱えばよいですか？

**A:** 秘密情報の安全な取り扱い：

**1. 環境変数での管理:**
```bash
# .envファイルに設定（コミットしない）
GITHUB_TOKEN=your_token_here
```

**2. CI/CD環境での設定:**
```yaml
# GitHub Actionsの場合
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**3. ローカル開発での注意:**
```bash
# トークンをコマンドラインに直接記述しない
# ログファイルに秘密情報が含まれないよう注意
```

### Q: コンテナのセキュリティは大丈夫ですか？

**A:** コンテナセキュリティの対策：

**1. 非root実行:**
- コンテナは非rootユーザーで実行
- 最小権限の原則を適用

**2. イメージの安全性:**
```bash
# セキュリティスキャンの実行
make security

# 脆弱性チェック
trivy image github-actions-simulator:latest
```

**3. ネットワーク分離:**
- Docker networkによる分離
- 不要なポートの公開を制限

## 📊 パフォーマンス

### Q: 実行が遅い場合の対処方法は？

**A:** パフォーマンス改善の方法：

**1. パフォーマンス監視の有効化:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- --show-performance-metrics
```

**2. 特定のジョブのみ実行:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- --job test
```

**3. Docker BuildKitの有効化:**
```bash
export DOCKER_BUILDKIT=1
./scripts/run-actions.sh .github/workflows/ci.yml
```

**4. キャッシュの活用:**
```bash
# Dockerイメージキャッシュの確認
docker images

# 不要なキャッシュのクリア
docker system prune -f
```

### Q: メモリ使用量を最適化するにはどうすればよいですか？

**A:** メモリ使用量の最適化：

**1. リソース監視:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- \
  --show-performance-metrics --show-execution-trace
```

**2. 不要なコンテナの削除:**
```bash
docker container prune -f
docker image prune -f
```

**3. メモリ制限の設定:**
```yaml
# docker-compose.override.yml
services:
  actions:
    mem_limit: 2g
    memswap_limit: 2g
```

### Q: 並列実行は可能ですか？

**A:** 並列実行の方法：

**1. 複数ジョブの並列実行:**
```bash
./scripts/run-actions.sh .github/workflows/ci.yml -- --parallel
```

**2. 複数ワークフローの並列実行:**
```bash
# 別々のターミナルで実行
./scripts/run-actions.sh .github/workflows/ci.yml &
./scripts/run-actions.sh .github/workflows/test.yml &
wait
```

**3. CI/CDでの並列実行:**
```yaml
# GitHub Actionsでのマトリクス実行
strategy:
  matrix:
    workflow: [ci.yml, test.yml, deploy.yml]
```

### Q: ディスク使用量を削減するにはどうすればよいですか？

**A:** ディスク使用量の削減：

**1. 定期的なクリーンアップ:**
```bash
make clean
docker system prune -f --volumes
```

**2. 不要なイメージの削除:**
```bash
docker image prune -a -f
```

**3. ログファイルの管理:**
```bash
# ログローテーションの設定
logrotate /etc/logrotate.d/docker-containers
```

## 📞 サポート・コミュニティ

### Q: 問題が解決しない場合はどこに相談すればよいですか？

**A:** サポートチャネル：

**1. ドキュメントの確認:**
- [USER_GUIDE.md](USER_GUIDE.md) - 詳細な利用方法
- [トラブルシューティング](../TROUBLESHOOTING.md) - 一般的な問題

**2. 診断情報の収集:**
```bash
./scripts/run-actions.sh --check-deps > system-info.txt
make version > version-info.txt
```

**3. GitHub Issues:**
- バグ報告: [Issues](https://github.com/scottlz0310/mcp-docker/issues)
- 機能要望: [Feature Requests](https://github.com/scottlz0310/mcp-docker/issues/new?template=feature_request.md)

**4. GitHub Discussions:**
- 質問・相談: [Discussions](https://github.com/scottlz0310/mcp-docker/discussions)

### Q: 貢献するにはどうすればよいですか？

**A:** プロジェクトへの貢献方法：

**1. ドキュメントの改善:**
- 誤字脱字の修正
- 使用例の追加
- 翻訳の提供

**2. バグ修正:**
- 問題の報告
- 修正パッチの提供
- テストケースの追加

**3. 機能追加:**
- 新機能の提案
- 実装とテスト
- ドキュメントの更新

**詳細:** [CONTRIBUTING.md](../../CONTRIBUTING.md)

### Q: 最新情報を入手するにはどうすればよいですか？

**A:** 最新情報の入手方法：

**1. GitHubリポジトリ:**
- [リポジトリ](https://github.com/scottlz0310/mcp-docker)をWatch
- [Releases](https://github.com/scottlz0310/mcp-docker/releases)をフォロー

**2. 変更履歴:**
- [CHANGELOG.md](../../CHANGELOG.md) - 詳細な変更履歴
- [リリースノート](https://github.com/scottlz0310/mcp-docker/releases) - 主要な変更

**3. バージョン確認:**
```bash
make version
```

---

## 📚 関連リソース

### 公式ドキュメント
- **[メインREADME](../../README.md)** - プロジェクト全体の概要
- **[USER_GUIDE.md](USER_GUIDE.md)** - 詳細な利用方法
- **[トラブルシューティング](../TROUBLESHOOTING.md)** - 問題解決ガイド

### 技術リソース
- **[nektos/act](https://github.com/nektos/act)** - GitHub Actions ローカル実行ツール
- **[Docker Documentation](https://docs.docker.com/)** - Docker 公式ドキュメント
- **[GitHub Actions Documentation](https://docs.github.com/en/actions)** - GitHub Actions 公式ドキュメント

### コミュニティ
- **[GitHub Issues](https://github.com/scottlz0310/mcp-docker/issues)** - バグ報告・機能要望
- **[GitHub Discussions](https://github.com/scottlz0310/mcp-docker/discussions)** - 質問・相談

---

このFAQがGitHub Actions Simulatorの効果的な活用に役立つことを願っています。さらに詳しい情報については、[詳細利用ガイド](USER_GUIDE.md)をご確認ください。
