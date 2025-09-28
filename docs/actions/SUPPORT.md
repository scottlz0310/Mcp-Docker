# 🆘 GitHub Actions Simulator - サポートガイド

## 📞 サポートチャネル

GitHub Actions Simulatorでは、複数のサポートチャネルを提供しています。問題の種類に応じて適切なチャネルをご利用ください。

### 🐛 バグ報告・機能要望

**GitHub Issues** (推奨)
- **URL**: [https://github.com/scottlz0310/mcp-docker/issues](https://github.com/scottlz0310/mcp-docker/issues)
- **用途**: バグ報告、機能要望、改善提案
- **対応時間**: 通常1-3営業日以内

### 💬 質問・ディスカッション

**GitHub Discussions**
- **URL**: [https://github.com/scottlz0310/mcp-docker/discussions](https://github.com/scottlz0310/mcp-docker/discussions)
- **用途**: 使用方法の質問、アイデア共有、コミュニティディスカッション
- **対応時間**: コミュニティベース

### 📚 ドキュメント

**包括的ドキュメント**
- **問題報告ガイド**: [docs/PROBLEM_REPORTING_GUIDE.md](PROBLEM_REPORTING_GUIDE.md)
- **コミュニティサポート**: [docs/COMMUNITY_SUPPORT_GUIDE.md](COMMUNITY_SUPPORT_GUIDE.md)
- **トラブルシューティング**: [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **ハングアップ対応**: [docs/HANGUP_TROUBLESHOOTING.md](HANGUP_TROUBLESHOOTING.md)
- **プラットフォーム対応**: [docs/PLATFORM_SUPPORT.md](PLATFORM_SUPPORT.md)
- **アップグレードガイド**: [docs/UPGRADE_GUIDE.md](UPGRADE_GUIDE.md)

## 🔍 問題報告前のセルフチェック

問題を報告する前に、以下の手順で自己診断を行ってください：

### 1. 自動診断ツールの実行

```bash
# 包括的な診断情報収集
./scripts/collect-support-info.sh

# 自動トラブルシューティング付き
./scripts/collect-support-info.sh --auto-troubleshoot

# 特定問題の診断
./scripts/diagnostic-helper.sh all
./scripts/diagnostic-helper.sh docker
./scripts/diagnostic-helper.sh permissions
```

### 2. 基本診断の実行

```bash
# 包括的な依存関係チェック
./scripts/run-actions.sh --check-deps

# 拡張診断（プラットフォーム最適化情報を含む）
./scripts/run-actions.sh --check-deps-extended

# バージョン情報の確認
make version
```

### 3. よくある問題の確認

以下のドキュメントで解決策を確認してください：

- **問題報告方法**: [docs/PROBLEM_REPORTING_GUIDE.md](PROBLEM_REPORTING_GUIDE.md)
- **コミュニティ活用**: [docs/COMMUNITY_SUPPORT_GUIDE.md](COMMUNITY_SUPPORT_GUIDE.md)
- **一般的な問題**: [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **実行停止問題**: [docs/HANGUP_TROUBLESHOOTING.md](HANGUP_TROUBLESHOOTING.md)
- **権限問題**: [docs/PERMISSION_SOLUTIONS.md](PERMISSION_SOLUTIONS.md)

### 4. 環境の確認

```bash
# 自動診断（推奨）
./scripts/collect-support-info.sh

# 手動システム情報収集
uname -a
docker --version
docker-compose --version
git --version
```

## 📋 効果的な問題報告方法

### 必須情報

問題を報告する際は、以下の情報を含めてください：

#### 1. 環境情報

```bash
# 診断情報を自動収集
./scripts/collect-support-info.sh
```

または手動で以下を収集：

```bash
echo "=== システム情報 ===" > support_info.txt
uname -a >> support_info.txt
echo "" >> support_info.txt

echo "=== バージョン情報 ===" >> support_info.txt
make version >> support_info.txt
echo "" >> support_info.txt

echo "=== Docker情報 ===" >> support_info.txt
docker --version >> support_info.txt
docker-compose --version >> support_info.txt
docker system info >> support_info.txt
echo "" >> support_info.txt

echo "=== 診断結果 ===" >> support_info.txt
./scripts/run-actions.sh --check-deps >> support_info.txt
```

#### 2. 問題の詳細

- **問題の概要**: 何が起こったか
- **期待される動作**: 何が起こるべきだったか
- **実際の動作**: 実際に何が起こったか
- **再現手順**: 問題を再現する具体的な手順
- **エラーメッセージ**: 完全なエラーメッセージ（あれば）

#### 3. 実行ログ

```bash
# 詳細ログ付きで実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --verbose > execution.log 2>&1

# Dockerログの収集
docker-compose logs > docker.log 2>&1
```

### 問題報告テンプレート

```markdown
## 問題の概要
[問題の簡潔な説明]

## 環境情報
- OS: [例: Ubuntu 22.04]
- Docker: [例: 24.0.7]
- Python: [例: 3.13.7]
- GitHub Actions Simulator: [例: v1.1.0]

## 再現手順
1. [手順1]
2. [手順2]
3. [手順3]

## 期待される動作
[何が起こるべきか]

## 実際の動作
[実際に何が起こったか]

## エラーメッセージ
```
[エラーメッセージをここに貼り付け]
```

## 追加情報
[診断情報、ログファイル、スクリーンショットなど]
```

## 🚀 自動診断・サポートツール

プロジェクトには包括的な診断とサポートツールが含まれています：

### サポート情報自動収集

```bash
# 基本的なサポート情報収集
./scripts/collect-support-info.sh

# 自動トラブルシューティング付き
./scripts/collect-support-info.sh --auto-troubleshoot

# 詳細情報を含む収集
./scripts/collect-support-info.sh --verbose --network --performance

# 収集された情報を確認
cat support_info.txt
```

### 診断ヘルパーツール

```bash
# 全ての問題を診断
./scripts/diagnostic-helper.sh all

# 特定の問題を診断
./scripts/diagnostic-helper.sh docker
./scripts/diagnostic-helper.sh permissions
./scripts/diagnostic-helper.sh ports

# 自動修復を試行
./scripts/diagnostic-helper.sh --fix all
./scripts/diagnostic-helper.sh --fix permissions
```

### 収集される情報

**基本情報**:
- システム情報（OS、アーキテクチャ）
- バージョン情報（Python、Docker、Git）
- 診断結果（依存関係チェック）
- Docker環境情報
- 実行ログ（最新の実行結果）

**拡張情報**（オプション）:
- ネットワーク設定とポート使用状況
- パフォーマンス情報（CPU、メモリ、ディスク）
- 自動トラブルシューティング結果
- 問題解決提案

## 🔧 緊急時の対処法

### 1. 完全リセット

```bash
# 環境を完全にリセット
make clean-all
docker system prune -f
make setup
make build
```

### 2. バックアップからの復旧

```bash
# 設定ファイルをリセット
cp .env.example .env
cp .pre-commit-config.yaml.sample .pre-commit-config.yaml

# 依存関係を再インストール
rm -rf .venv
uv sync
```

### 3. 前のバージョンに戻す

```bash
# 前のコミットに戻る
git log --oneline -10  # 最近のコミットを確認
git checkout <前のコミットハッシュ>

# または前のタグに戻る
git tag -l  # 利用可能なタグを確認
git checkout v1.0.0  # 特定のバージョンに戻る
```

## 📈 サポート品質向上への貢献

### フィードバックの提供

- **ドキュメントの改善提案**: 分かりにくい部分の指摘
- **FAQ項目の提案**: よくある質問の追加
- **エラーメッセージの改善**: より分かりやすいメッセージの提案

### コミュニティサポート

- **GitHub Discussions**: 他のユーザーの質問への回答
- **ドキュメント改善**: プルリクエストでの貢献
- **バグ修正**: 問題の修正への貢献

## 🎯 サポートレベル

### コミュニティサポート（無料）

- **GitHub Issues**: バグ報告・機能要望
- **GitHub Discussions**: 質問・ディスカッション
- **ドキュメント**: 包括的なセルフヘルプ資料
- **対応時間**: ベストエフォート（通常1-3営業日）

### 企業サポート（検討中）

将来的に以下のサポートオプションを検討しています：

- **優先サポート**: 24時間以内の対応
- **カスタマイズ支援**: 特定要件への対応
- **トレーニング**: チーム向けトレーニングセッション
- **SLA保証**: サービスレベル保証

## 📞 緊急連絡先

### 重大なセキュリティ問題

セキュリティに関する重大な問題を発見した場合：

1. **公開Issues作成は避ける**
2. **プライベート報告**: GitHub Security Advisoriesを使用
3. **詳細情報**: 問題の詳細と影響範囲を記載

### システム障害

- **GitHub Status**: [https://www.githubstatus.com/](https://www.githubstatus.com/)
- **Docker Status**: [https://status.docker.com/](https://status.docker.com/)

## 🔄 サポート改善サイクル

### 継続的改善

1. **フィードバック収集**: ユーザーからの意見収集
2. **問題分析**: よくある問題の特定
3. **ドキュメント改善**: FAQ・トラブルシューティング更新
4. **ツール改善**: 診断機能・エラーメッセージ改善

### 品質指標

- **初回解決率**: 最初の回答で問題が解決する割合
- **平均対応時間**: 問題報告から初回回答までの時間
- **ユーザー満足度**: フィードバックベースの満足度評価

## 📚 関連リソース

### 公式ドキュメント

- **README**: [../README.md](../README.md) - プロジェクト概要
- **CONTRIBUTING**: [../CONTRIBUTING.md](../CONTRIBUTING.md) - 貢献ガイド
- **CHANGELOG**: [../CHANGELOG.md](../CHANGELOG.md) - 変更履歴

### 外部リソース

- **Docker Documentation**: [https://docs.docker.com/](https://docs.docker.com/)
- **GitHub Actions Documentation**: [https://docs.github.com/actions](https://docs.github.com/actions)
- **act Documentation**: [https://github.com/nektos/act](https://github.com/nektos/act)

---

**GitHub Actions Simulator** - あなたの成功をサポートします 🚀

問題解決のお手伝いをさせていただきます。遠慮なくお声がけください！
