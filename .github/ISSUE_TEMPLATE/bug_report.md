---
name: 🐛 バグ報告
about: バグや問題を報告する
title: '[BUG] '
labels: ['bug', 'needs-triage']
assignees: ''
---

## 🐛 問題の概要

**問題の簡潔な説明**
何が起こったかを簡潔に説明してください。

## 🔍 環境情報

**自動診断情報の収集**
以下のコマンドを実行して、診断情報を収集してください：

```bash
./scripts/collect-support-info.sh
```

収集された `support_info.txt` の内容をここに貼り付けてください：

```
[support_info.txt の内容をここに貼り付け]
```

**手動環境情報（自動収集が失敗した場合）**
- OS: [例: Ubuntu 22.04, macOS 13.0, Windows 11 + WSL2]
- Docker: [例: 24.0.7]
- Docker Compose: [例: 2.21.0]
- Python: [例: 3.13.7]
- uv: [例: 0.4.18]
- Git: [例: 2.34.1]
- GitHub Actions Simulator: [例: v1.2.0]

## 🔄 再現手順

問題を再現するための具体的な手順：

1. [手順1]
2. [手順2]
3. [手順3]
4. [エラーが発生]

**使用したコマンド**
```bash
# 実行したコマンドをここに記載
```

## 💭 期待される動作

何が起こるべきだったかを説明してください。

## 🚨 実際の動作

実際に何が起こったかを説明してください。

## 📋 エラーメッセージ

完全なエラーメッセージがあれば貼り付けてください：

```
[エラーメッセージをここに貼り付け]
```

## 📁 ログファイル

関連するログファイルがあれば添付してください：

**実行ログ**
```bash
# 詳細ログ付きで実行
./scripts/run-actions.sh .github/workflows/ci.yml -- --verbose > execution.log 2>&1
```

**Dockerログ**
```bash
# Docker Composeログの収集
docker-compose logs > docker.log 2>&1
```

## 🖼️ スクリーンショット

該当する場合、スクリーンショットを添付してください。

## 🔧 試行した解決策

問題解決のために既に試したことがあれば記載してください：

- [ ] [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) を確認した
- [ ] [docs/HANGUP_TROUBLESHOOTING.md](../docs/HANGUP_TROUBLESHOOTING.md) を確認した
- [ ] `./scripts/run-actions.sh --check-deps` を実行した
- [ ] Docker環境をリセットした (`make clean-all`)
- [ ] 依存関係を再インストールした
- [ ] その他: [記載してください]

## 📚 追加情報

問題の理解に役立つその他の情報があれば記載してください。

## ✅ チェックリスト

問題報告前に以下を確認してください：

- [ ] 最新バージョンを使用している
- [ ] [既存のIssues](https://github.com/scottlz0310/mcp-docker/issues)で同様の問題が報告されていないか確認した
- [ ] [トラブルシューティングガイド](../docs/TROUBLESHOOTING.md)を確認した
- [ ] 診断情報を収集した (`./scripts/collect-support-info.sh`)
- [ ] 機密情報（パスワード、トークンなど）が含まれていないか確認した

---

**サポートチーム**より: 詳細な情報をご提供いただき、ありがとうございます。迅速な問題解決のため、上記の情報をできるだけ完全に記載してください。
