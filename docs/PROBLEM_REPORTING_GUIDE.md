# 🆘 問題報告ガイド

GitHub Actions Simulatorで問題が発生した場合の効果的な報告方法について説明します。

## 📋 報告前のセルフチェック

問題を報告する前に、以下の手順で自己診断を行ってください：

### 1. 自動診断の実行

```bash
# 包括的な診断情報を収集
./scripts/collect-support-info.sh

# 拡張診断（利用可能な場合）
./scripts/run-actions.sh --check-deps-extended
```

### 2. 基本的なトラブルシューティング

```bash
# 環境の完全リセット
make clean-all
make setup
make build

# 依存関係の再確認
./scripts/run-actions.sh --check-deps

# バージョン情報の確認
make version
```

### 3. ドキュメントの確認

以下のドキュメントで解決策を確認してください：

- **[トラブルシューティング](TROUBLESHOOTING.md)** - 一般的な問題と解決方法
- **[ハングアップ対応](HANGUP_TROUBLESHOOTING.md)** - 実行停止問題の対処法
- **[プラットフォーム対応](PLATFORM_SUPPORT.md)** - OS固有の問題
- **[権限問題](PERMISSION_SOLUTIONS.md)** - 権限関連の問題

## 🎯 問題の種類別報告方法

### 🐛 バグ報告

**使用するテンプレート**: [Bug Report Template](../.github/ISSUE_TEMPLATE/bug_report.md)

**必須情報**:
1. **環境情報**: `./scripts/collect-support-info.sh` の出力
2. **再現手順**: 具体的なコマンドと手順
3. **期待される動作**: 何が起こるべきか
4. **実際の動作**: 実際に何が起こったか
5. **エラーメッセージ**: 完全なエラーログ

**効果的なバグ報告の例**:

```markdown
## 問題の概要
Docker Composeでサービス起動時にポート競合エラーが発生

## 再現手順
1. `make start` を実行
2. 以下のエラーが表示される

## エラーメッセージ
```
Error: bind: address already in use
```

## 環境情報
[collect-support-info.sh の出力]
```

### 🚀 機能要望

**使用するテンプレート**: [Feature Request Template](../.github/ISSUE_TEMPLATE/feature_request.md)

**重要なポイント**:
1. **動機の明確化**: なぜその機能が必要か
2. **具体的な仕様**: どのような動作を期待するか
3. **影響範囲**: 既存機能への影響
4. **代替案**: 他の解決方法の検討

### ❓ 質問・サポート

**使用するテンプレート**: [Question Template](../.github/ISSUE_TEMPLATE/question.md)

**または**: [GitHub Discussions](https://github.com/scottlz0310/mcp-docker/discussions)

**適切な質問の仕方**:
1. **目標の明確化**: 何を達成したいか
2. **現在の状況**: 何を試したか
3. **具体的な問題**: どこで困っているか

## 🔍 効果的な情報収集

### 診断情報の自動収集

```bash
# 基本診断情報
./scripts/collect-support-info.sh

# カスタム出力ファイル
./scripts/collect-support-info.sh --output my_issue.txt

# 詳細情報を含める
./scripts/collect-support-info.sh --verbose

# Docker情報を除外
./scripts/collect-support-info.sh --no-docker
```

### 手動情報収集

自動収集が失敗した場合の手動収集方法：

```bash
# システム情報
echo "=== システム情報 ===" > manual_info.txt
uname -a >> manual_info.txt
whoami >> manual_info.txt
pwd >> manual_info.txt

# バージョン情報
echo "=== バージョン情報 ===" >> manual_info.txt
docker --version >> manual_info.txt
docker-compose --version >> manual_info.txt
python3 --version >> manual_info.txt
git --version >> manual_info.txt

# 実行ログ
echo "=== 実行ログ ===" >> manual_info.txt
./scripts/run-actions.sh .github/workflows/ci.yml -- --verbose >> manual_info.txt 2>&1
```

### ログファイルの収集

```bash
# Docker Composeログ
docker-compose logs > docker_logs.txt 2>&1

# 特定サービスのログ
docker-compose logs actions-service > actions_logs.txt 2>&1

# プロジェクト固有のログ
find . -name "*.log" -type f -exec echo "=== {} ===" \; -exec cat {} \;
```

## 📊 問題の優先度設定

### 🔴 緊急 (Critical)

- **システムが完全に動作しない**
- **セキュリティ上の重大な問題**
- **データ損失の可能性**

**対応時間**: 24時間以内

### 🟡 高 (High)

- **主要機能が動作しない**
- **回避策が困難**
- **多くのユーザーに影響**

**対応時間**: 1-3営業日

### 🟢 中 (Medium)

- **一部機能に問題**
- **回避策が存在**
- **限定的な影響**

**対応時間**: 1週間以内

### ⚪ 低 (Low)

- **軽微な問題**
- **改善提案**
- **ドキュメント修正**

**対応時間**: ベストエフォート

## 🔒 機密情報の取り扱い

### 含めてはいけない情報

- **パスワード、APIキー、トークン**
- **個人情報（メールアドレス、名前）**
- **企業固有の設定や情報**
- **プライベートリポジトリの内容**

### 安全な情報共有

```bash
# 環境変数から機密情報を除外
env | grep -v -E "(PASSWORD|TOKEN|KEY|SECRET)" > safe_env.txt

# ログから機密情報をマスク
sed 's/password=[^[:space:]]*/password=***MASKED***/g' original.log > safe.log
```

## 📞 サポートチャネルの使い分け

### GitHub Issues

**適用場面**:
- バグ報告
- 機能要望
- 明確な問題の報告

**メリット**:
- 公開追跡可能
- 開発チームの直接対応
- 他のユーザーの参考になる

### GitHub Discussions

**適用場面**:
- 一般的な質問
- 使用方法の相談
- アイデアの共有
- コミュニティディスカッション

**メリット**:
- カジュアルな議論
- コミュニティサポート
- ナレッジ共有

### プライベート報告

**適用場面**:
- セキュリティ問題
- 機密性の高い問題

**方法**:
- GitHub Security Advisories
- メンテナーへの直接連絡

## 🚀 報告後のフォローアップ

### 追加情報の提供

- **迅速な応答**: 追加情報の要求には速やかに対応
- **テスト協力**: 修正版のテストに協力
- **フィードバック**: 解決策の評価とフィードバック

### 解決の確認

- **動作確認**: 修正が期待通りに動作するか確認
- **回帰テスト**: 他の機能に影響がないか確認
- **ドキュメント確認**: 関連ドキュメントの更新確認

## 📈 品質向上への貢献

### 良い報告の特徴

- **再現可能**: 他の人が同じ問題を再現できる
- **具体的**: 曖昧な表現を避け、具体的な情報を提供
- **完全**: 必要な情報がすべて含まれている
- **整理された**: 情報が論理的に整理されている

### コミュニティへの貢献

- **解決策の共有**: 問題を解決した場合、方法を共有
- **ドキュメント改善**: 不明確な部分の改善提案
- **他のユーザー支援**: 同様の問題を抱えるユーザーの支援

## 🎯 よくある報告ミス

### 避けるべき報告

❌ **情報不足**
```
「動かない」「エラーが出る」
```

✅ **適切な報告**
```
「make start実行時にポート8080でbind errorが発生」
+ 完全なエラーメッセージ
+ 環境情報
+ 再現手順
```

❌ **重複報告**
```
既存のIssueを確認せずに同じ問題を報告
```

✅ **適切な対応**
```
既存のIssueにコメントで追加情報を提供
```

❌ **機密情報の漏洩**
```
パスワードやAPIキーを含むログを貼り付け
```

✅ **安全な共有**
```
機密情報をマスクまたは除外した情報を共有
```

## 📚 関連リソース

### 公式ドキュメント

- **[サポートガイド](SUPPORT.md)** - 包括的なサポート情報
- **[トラブルシューティング](TROUBLESHOOTING.md)** - 問題解決ガイド
- **[貢献ガイド](../CONTRIBUTING.md)** - プロジェクトへの貢献方法

### 外部リソース

- **[GitHub Issues ガイド](https://docs.github.com/en/issues)** - GitHub Issues の使い方
- **[Markdown ガイド](https://docs.github.com/en/get-started/writing-on-github)** - 効果的な文書作成

---

**効果的な問題報告により、より良いツールを一緒に作り上げましょう！** 🚀
