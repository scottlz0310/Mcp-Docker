---
name: ❓ 質問・サポート
about: 使用方法や設定に関する質問
title: '[QUESTION] '
labels: ['question', 'needs-triage']
assignees: ''
---

## ❓ 質問の概要

**何について質問したいか**
質問内容を簡潔に説明してください。

## 🎯 達成したいこと

**最終的に何を実現したいか**
あなたが達成しようとしている目標を説明してください。

## 🔍 現在の状況

**現在の設定や環境**
- OS: [例: Ubuntu 22.04]
- Docker: [例: 24.0.7]
- GitHub Actions Simulator: [例: v1.2.0]

**現在試していること**
```bash
# 実行しているコマンドや設定
```

**現在の結果**
```
現在得られている結果や出力
```

## 📚 確認済みのリソース

質問前に確認したドキュメントにチェックを入れてください：

- [ ] [README.md](../../README.md) - プロジェクト概要
- [ ] [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) - トラブルシューティング
- [ ] [docs/actions/README.md](../docs/actions/README.md) - 使用方法
- [ ] [docs/PLATFORM_SUPPORT.md](../docs/PLATFORM_SUPPORT.md) - プラットフォーム対応
- [ ] [docs/DEVELOPMENT_WORKFLOW_INTEGRATION.md](../docs/DEVELOPMENT_WORKFLOW_INTEGRATION.md) - ワークフロー統合
- [ ] [既存のIssues](https://github.com/scottlz0310/mcp-docker/issues)
- [ ] [GitHub Discussions](https://github.com/scottlz0310/mcp-docker/discussions)

## 🔧 試行した解決策

**既に試したこと**
問題解決のために試したことがあれば記載してください：

- [ ] 基本診断を実行した (`./scripts/run-actions.sh --check-deps`)
- [ ] 環境をリセットした (`make clean-all && make setup`)
- [ ] 依存関係を再インストールした
- [ ] 設定ファイルを確認した
- [ ] その他: [記載してください]

## 📋 エラーメッセージ（該当する場合）

エラーが発生している場合、完全なエラーメッセージを貼り付けてください：

```
[エラーメッセージをここに貼り付け]
```

## 🎨 期待される動作

**どのような動作を期待しているか**
理想的な結果や動作を説明してください。

## 📁 設定ファイル（該当する場合）

関連する設定ファイルの内容を貼り付けてください（機密情報は除く）：

**docker-compose.yml**
```yaml
# 関連部分のみ
```

**.env（機密情報を除く）**
```bash
# 関連する環境変数のみ
```

**ワークフローファイル**
```yaml
# 問題のあるワークフロー部分
```

## 🔍 診断情報

以下のコマンドを実行して診断情報を収集してください：

```bash
./scripts/collect-support-info.sh --output question_info.txt
```

収集された情報の関連部分をここに貼り付けてください：

```
[診断情報の関連部分]
```

## 🌐 使用ケース

**具体的な使用シナリオ**
どのような場面でこの機能を使用しようとしているかを説明してください。

## 📊 緊急度

**この質問の緊急度**
- [ ] 🔴 緊急 - 作業がブロックされている
- [ ] 🟡 通常 - 改善したいが回避策がある
- [ ] 🟢 低 - 時間があるときに解決したい

## 💡 追加情報

**その他の関連情報**
質問の理解に役立つその他の情報があれば記載してください。

## ✅ チェックリスト

質問投稿前に以下を確認してください：

- [ ] 質問内容が明確で具体的である
- [ ] 関連するドキュメントを確認した
- [ ] 既存のIssuesやDiscussionsを検索した
- [ ] 機密情報（パスワード、トークンなど）を含めていない
- [ ] 診断情報を収集した（該当する場合）
- [ ] 期待される動作を明確に説明した

---

**コミュニティ**より: ご質問ありがとうございます！詳細な情報により、より適切なサポートを提供できます。[GitHub Discussions](https://github.com/scottlz0310/mcp-docker/discussions)での議論も歓迎します。
