# Contributing to MCP Docker Environment

## 開発フロー

### 1. Issue作成
- 機能追加・バグ修正前にIssueを作成
- テンプレートに従って詳細を記載

### 2. ブランチ作成
```bash
git checkout -b feature/your-feature-name
git checkout -b fix/bug-description
```

### 3. 開発・テスト
```bash
# ローカルテスト
make test

# Docker build確認
make build
```

### 4. Pull Request
- ドラフトPRで早期フィードバック
- レビュー後にマージ

## コミット規約

Conventional Commits準拠：

```
feat: 新機能追加
fix: バグ修正
docs: ドキュメント更新
refactor: リファクタリング
test: テスト追加・修正
chore: その他の変更
ci: CI/CD設定変更
```

## 品質基準

- [ ] Docker build成功
- [ ] 全サービス起動確認
- [ ] セキュリティチェック通過
- [ ] ドキュメント更新

## 開発環境

### 必要なツール
- Docker & Docker Compose
- Make
- Git

### セットアップ
```bash
# 初期設定
make setup

# 開発開始
make dev
```

## レビュープロセス

1. **自動チェック**: CI/CDでの品質確認
2. **コードレビュー**: 最低1名の承認必要
3. **統合テスト**: 全サービス動作確認
4. **マージ**: squash mergeを推奨

## 質問・サポート

- Issue作成でお気軽にご質問ください
- 開発に関する議論はDiscussionsをご利用ください