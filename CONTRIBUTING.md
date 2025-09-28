# 🤝 GitHub Actions Simulator - 貢献ガイド

GitHub Actions Simulatorプロジェクトへの貢献を歓迎します！このガイドでは、効果的に貢献するための手順とベストプラクティスを説明します。

## 🎯 貢献の種類

### 🐛 バグ修正
- 既存の問題の修正
- エラーハンドリングの改善
- パフォーマンスの最適化

### ✨ 新機能開発
- 新しいシミュレーション機能
- プラットフォーム対応の拡張
- ユーザビリティの向上

### 📚 ドキュメント改善
- 使用方法の説明追加
- トラブルシューティングガイド更新
- コード例の追加

### 🧪 テスト強化
- テストカバレッジの向上
- 新しいテストケースの追加
- CI/CDパイプラインの改善

## 🚀 開発フロー

### 1. 事前準備

#### Issue作成
```bash
# 機能追加・バグ修正前にIssueを作成
# テンプレートに従って詳細を記載
# ラベルを適切に設定
```

#### 開発環境セットアップ
```bash
# リポジトリをフォーク・クローン
git clone https://github.com/your-username/mcp-docker.git
cd mcp-docker

# 開発依存関係をインストール
uv sync --group dev

# Pre-commitフックを設定
cp .pre-commit-config.yaml.sample .pre-commit-config.yaml
pre-commit install

# 環境を構築
make setup
make build
```

### 2. ブランチ戦略

```bash
# 機能開発
git checkout -b feature/lightweight-improvement
git checkout -b feature/new-platform-support

# バグ修正
git checkout -b fix/docker-permission-issue
git checkout -b fix/hangup-detection

# ドキュメント更新
git checkout -b docs/update-troubleshooting
git checkout -b docs/add-examples

# CI/CD改善
git checkout -b ci/improve-test-coverage
git checkout -b ci/add-security-scan
```

### 3. 開発・テスト

#### 基本開発サイクル
```bash
# 開発開始
make actions  # 動作確認

# コード品質チェック
make pre-commit              # 全品質チェック実行
pre-commit run --all-files   # 全ファイルでチェック

# テスト実行
make test                    # 基本テスト
make test-all               # 全テストスイート

# セキュリティチェック
make security

# Docker環境確認
make build
./scripts/run-actions.sh --check-deps
```

#### 品質基準チェックリスト
- [ ] **Docker build成功**: `make build`
- [ ] **全サービス起動確認**: `make actions`
- [ ] **テスト通過**: `make test-all`
- [ ] **セキュリティチェック通過**: `make security`
- [ ] **ドキュメント更新**: 関連ドキュメントの更新
- [ ] **Pre-commit通過**: `pre-commit run --all-files`

### 4. Pull Request

#### PR作成前チェック
```bash
# 最新のmainブランチと同期
git checkout main
git pull upstream main
git checkout your-feature-branch
git rebase main

# 最終テスト
make test-all
make security
```

#### PR作成
- **ドラフトPR**: 早期フィードバックのため
- **詳細な説明**: 変更内容と理由を明記
- **関連Issue**: `Closes #123` でIssueをリンク
- **スクリーンショット**: UI変更がある場合

## 📝 コミット規約

### Conventional Commits準拠

```bash
# 新機能
feat: GitHub Actions Simulatorに新しいプラットフォーム対応を追加

# バグ修正
fix: Docker権限エラーの自動復旧機能を修正

# ドキュメント
docs: トラブルシューティングガイドにmacOS対応を追加

# リファクタリング
refactor: 診断サービスのコード構造を改善

# テスト
test: ハングアップ検出機能のテストケースを追加

# その他
chore: 依存関係を最新バージョンに更新

# CI/CD
ci: GitHub Actionsワークフローにセキュリティスキャンを追加

# パフォーマンス
perf: Docker イメージビルド時間を30%短縮

# ビルド
build: uvパッケージ管理の設定を最適化
```

### コミットメッセージのベストプラクティス

```bash
# 良い例
feat: 軽量actベースアーキテクチャに自動復旧機能を追加

- Docker接続エラー時の自動再接続
- プロセスハングアップ時の自動再起動
- バッファクリア機能の統合
- プラットフォーム別エラーガイダンス

Closes #123

# 悪い例
fix: バグ修正
update: ファイル更新
```

## 🏗️ 開発環境

### 必要なツール

#### 必須
- **Docker** (20.10+) & **Docker Compose** (2.0+)
- **Python** (3.13+)
- **uv** (パッケージ管理)
- **Git** (2.20+)
- **Make** (ビルドツール)

#### 推奨
- **pre-commit** (品質チェック)
- **act** (ローカルGitHub Actions実行)

### 開発環境セットアップ

#### 初期セットアップ
```bash
# 1. 依存関係確認
./scripts/run-actions.sh --check-deps

# 2. 開発依存関係インストール
uv sync --group dev

# 3. Pre-commitフック設定
cp .pre-commit-config.yaml.sample .pre-commit-config.yaml
pre-commit install

# 4. 環境構築
make setup
make build

# 5. 動作確認
make test
./scripts/run-actions.sh
```

#### 日常的な開発コマンド
```bash
# 開発サーバー起動
make actions

# 品質チェック
make pre-commit

# テスト実行
make test                    # 基本テスト
make test-hangup-quick      # 高速ハングアップテスト
make test-all               # 全テストスイート

# セキュリティチェック
make security

# 環境クリーンアップ
make clean
```

## 🔍 レビュープロセス

### 自動チェック
1. **CI/CDパイプライン**: GitHub Actionsでの自動テスト
2. **品質ゲート**: pre-commit、セキュリティスキャン
3. **プラットフォームテスト**: Linux、macOS、Windows (WSL)

### 人的レビュー
1. **コードレビュー**: 最低1名の承認必要
2. **設計レビュー**: 大きな変更の場合
3. **ドキュメントレビュー**: 使いやすさの確認

### マージ要件
- [ ] 全自動テスト通過
- [ ] 最低1名の承認
- [ ] 競合解決済み
- [ ] ドキュメント更新済み

## 🎨 コーディング規約

### Python
```python
# PEP 8準拠
# Type hintsの使用
# Docstringの記載

def simulate_workflow(workflow_file: str, options: Dict[str, Any]) -> SimulationResult:
    """
    GitHub Actionsワークフローをシミュレートします。

    Args:
        workflow_file: ワークフローファイルのパス
        options: シミュレーションオプション

    Returns:
        SimulationResult: シミュレーション結果

    Raises:
        WorkflowError: ワークフローファイルが無効な場合
    """
    pass
```

### Shell Script
```bash
#!/bin/bash
# POSIX準拠
# エラーハンドリング必須
# 関数の使用推奨

set -euo pipefail

# 関数定義
check_dependencies() {
    local required_commands=("docker" "uv" "git")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "必要なコマンドが見つかりません: $cmd"
            return 1
        fi
    done
}
```

### Docker
```dockerfile
# マルチステージビルド
# 非rootユーザー実行
# 最小権限の原則

FROM python:3.13-alpine AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.13-alpine
RUN adduser -D -s /bin/sh appuser
USER appuser
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
```

## 🧪 テスト戦略

### テストの種類

#### 単体テスト
```bash
# Python単体テスト
uv run pytest tests/unit/

# Shell script テスト
bats tests/unit/test_scripts.bats
```

#### 統合テスト
```bash
# Docker環境テスト
make test

# エンドツーエンドテスト
make test-e2e
```

#### セキュリティテスト
```bash
# 脆弱性スキャン
make security

# 依存関係監査
make audit-deps
```

### テスト作成ガイドライン

```python
# tests/test_example.py
import pytest
from unittest.mock import Mock, patch

class TestWorkflowSimulation:
    """ワークフローシミュレーション機能のテスト"""

    def test_successful_simulation(self):
        """正常なシミュレーション実行のテスト"""
        # Given
        workflow_file = ".github/workflows/ci.yml"

        # When
        result = simulate_workflow(workflow_file)

        # Then
        assert result.success is True
        assert result.exit_code == 0

    @patch('docker.from_env')
    def test_docker_connection_error(self, mock_docker):
        """Docker接続エラー時のテスト"""
        # Given
        mock_docker.side_effect = ConnectionError("Docker daemon not running")

        # When & Then
        with pytest.raises(DockerConnectionError):
            simulate_workflow(".github/workflows/ci.yml")
```

## 📚 ドキュメント貢献

### ドキュメント構造
```
docs/
├── README.md                    # プロジェクト概要
├── TROUBLESHOOTING.md          # トラブルシューティング
├── PLATFORM_SUPPORT.md        # プラットフォーム対応
├── UPGRADE_GUIDE.md            # アップグレードガイド
├── SUPPORT.md                  # サポート情報
└── actions/                    # Actions固有ドキュメント
    ├── USER_GUIDE.md
    └── FAQ.md
```

### ドキュメント作成ガイドライン

```markdown
# タイトル（H1は1つのみ）

## 概要
簡潔な説明

## 前提条件
- 必要な環境
- 前提知識

## 手順
### ステップ1
具体的な手順

```bash
# コマンド例
make test
```

### ステップ2
次の手順

## トラブルシューティング
よくある問題と解決方法

## 関連リソース
- [関連ドキュメント](docs/)
```

## 🌍 国際化・多言語対応

### 現在の対応状況
- **日本語**: 完全対応（メイン言語）
- **英語**: 部分対応（README、コメント）

### 多言語対応への貢献
```bash
# 英語ドキュメント作成
docs/en/README.md
docs/en/TROUBLESHOOTING.md

# 翻訳の品質確認
# 技術用語の統一
# 文化的な配慮
```

## 🏆 貢献者認定

### 貢献レベル

#### 🥉 ブロンズ貢献者
- 初回PR マージ
- ドキュメント改善
- バグ報告

#### 🥈 シルバー貢献者
- 複数のPR マージ
- 機能追加
- テスト改善

#### 🥇 ゴールド貢献者
- 継続的な貢献
- メンテナンス支援
- コミュニティサポート

### 認定特典
- **README.md**: 貢献者リストに掲載
- **GitHub Profile**: 貢献バッジ表示
- **優先サポート**: 問題報告時の優先対応

## 📞 質問・サポート

### 開発に関する質問
- **GitHub Discussions**: [技術的な質問・アイデア共有](https://github.com/scottlz0310/mcp-docker/discussions)
- **GitHub Issues**: [バグ報告・機能要望](https://github.com/scottlz0310/mcp-docker/issues)

### リアルタイムサポート
- **Issue コメント**: 迅速な回答
- **PR レビュー**: 建設的なフィードバック

### 貢献者向けリソース
- **開発ガイド**: [docs/DEVELOPMENT_WORKFLOW_INTEGRATION.md](docs/DEVELOPMENT_WORKFLOW_INTEGRATION.md)
- **リリースプロセス**: [docs/RELEASE_SYSTEM.md](docs/RELEASE_SYSTEM.md)
- **アーキテクチャ**: [docs/VALUE_PROPOSITION.md](docs/VALUE_PROPOSITION.md)

## 🎉 貢献者一覧

### メンテナー
- **scottlz0310** - プロジェクト創設者・メインメンテナー

### 貢献者
<!-- 貢献者リストは自動更新されます -->

## 📄 ライセンス

このプロジェクトに貢献することで、あなたの貢献が [MIT License](LICENSE) の下で公開されることに同意したものとみなされます。

---

**GitHub Actions Simulator** - あなたの貢献をお待ちしています！ 🚀

一緒により良いツールを作りましょう。どんな小さな貢献でも大歓迎です！
