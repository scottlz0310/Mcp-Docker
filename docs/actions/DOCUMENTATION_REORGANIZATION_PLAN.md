# ドキュメント整理計画

## 🎯 目的

プロジェクトのドキュメントを `docs/actions/` と `.kiro/` に集約し、明確な構造を作る。

## 📁 新しいドキュメント構造

### `docs/actions/` - ユーザー向けドキュメント
```
docs/actions/
├── README.md                    # Actions Simulator メインドキュメント
├── USER_GUIDE.md               # ユーザーガイド
├── FAQ.md                      # よくある質問
├── TROUBLESHOOTING.md          # トラブルシューティング
├── CLI_REFERENCE.md            # CLIリファレンス
├── API_REFERENCE.md            # APIリファレンス
├── PLATFORM_SUPPORT.md         # プラットフォーム対応
├── INSTALLATION.md             # インストールガイド
├── QUICK_START.md              # クイックスタート
├── EXAMPLES.md                 # 使用例集
├── PERFORMANCE.md              # パフォーマンスガイド
├── SECURITY.md                 # セキュリティガイド
├── UPGRADE_GUIDE.md            # アップグレードガイド
├── DEVELOPMENT.md              # 開発者ガイド
├── CONTRIBUTING.md             # 貢献ガイド
└── CHANGELOG.md                # 変更履歴
```

### `.kiro/` - 開発・設計ドキュメント
```
.kiro/
├── steering/                   # Kiro AI ステアリングルール
│   ├── docker-implementation-rules.md
│   ├── docker-quality-rules.md
│   └── project-guidelines.md
├── specs/                      # 仕様・設計ドキュメント
│   ├── architecture/
│   ├── implementation/
│   └── quality-gates/
└── docs/                       # 内部ドキュメント
    ├── design-decisions.md
    ├── implementation-notes.md
    └── quality-standards.md
```

## 🔄 移行計画

### Phase 1: 重要ドキュメントの移行
1. Actions Simulator関連ドキュメントを `docs/actions/` に移行
2. 設計・実装ドキュメントを `.kiro/specs/` に移行
3. 品質・ルールドキュメントを `.kiro/steering/` に整理

### Phase 2: 統合・整理
1. 重複ドキュメントの統合
2. リンク切れの修正
3. 目次・索引の作成

### Phase 3: 品質向上
1. ドキュメント品質チェック
2. アクセシビリティ改善
3. 自動生成システムの構築
