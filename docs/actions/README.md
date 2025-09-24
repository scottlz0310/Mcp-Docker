# GitHub Actions Simulator - ドキュメント目次

## 📚 ドキュメント構成

### 📖 設計・アーキテクチャ
- [github-actions-simulator-design.md](github-actions-simulator-design.md) - 包括的技術設計書（27KB）
- [github-actions-simulator-summary.md](github-actions-simulator-summary.md) - プロジェクト概要
- [actions-service-proposal.md](actions-service-proposal.md) - 新規サービス提案書

### 🛠️ 実装・統合
- [implementation-plan.md](implementation-plan.md) - 詳細実装計画（5週間）
- [act-integration-design.md](act-integration-design.md) - act統合技術仕様
- [codeql-integration-strategy.md](codeql-integration-strategy.md) - CodeQL統合戦略

### 🎨 ユーザーインターフェース
- [ui-design.md](ui-design.md) - CLI・REST API設計

### 🔌 外部連携
- [external-api-specification.md](external-api-specification.md) - 外部呼び出しAPI仕様書

## 🎯 読み始める順序

### 1. プロジェクト理解
1. `github-actions-simulator-summary.md` - 概要把握
2. `actions-service-proposal.md` - 最終アーキテクチャ理解

### 2. 技術詳細
1. `github-actions-simulator-design.md` - 技術仕様
2. `act-integration-design.md` - act統合方法
3. `codeql-integration-strategy.md` - CodeQL統合

### 3. 実装準備
1. `implementation-plan.md` - 開発計画
2. `ui-design.md` - インターフェース設計
3. `external-api-specification.md` - API仕様

## 🚀 実装開始

すべてのドキュメントが完成し、実装開始準備完了：

```bash
# Phase 1 開始: 基本構造作成
mkdir -p services/actions
python main.py actions simulate .github/workflows/ci.yml
```

## 📝 更新履歴

- **2025-09-25**: ドキュメント整理・`docs/actions/`フォルダに集約
- **2025-09-25**: 外部API仕様書追加
- **2025-09-25**: CodeQL統合戦略決定
- **2025-09-25**: act統合技術選択
