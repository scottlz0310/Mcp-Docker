# プロジェクト分析ドキュメント

このディレクトリには、Mcp-Docker プロジェクトの問題点分析と改善提案がまとめられています。

---

## 🎯 プロジェクトの正しい目的

**Mcp-Docker は:**
- ✅ Dockerサーバーをローカルで管理するツール
- ✅ 各種MCPサーバーやツールをコンテナで統一管理
- ✅ 他の自分のリポジトリから簡単に利用できるようにする
- ✅ サービスは今後も増やす予定（管理はシンプルに）

**ではない:**
- ❌ PyPI公開するライブラリ
- ❌ Python APIを提供するSDK
- ❌ 単一目的のツール

**技術方針:**
- ✅ Python 3.13+ 使用（最新バージョン）
- ✅ uv 使用（モダンで高速なパッケージマネージャー）
- ✅ Dockerイメージでの提供
- ✅ examples/ で使用例を提供

---

## 📚 ドキュメント一覧

### ⭐ 1. [Dockerサーバー管理のシンプル化提案](docker-server-management.md) **← メイン提案**

**正しい目的に基づいた**シンプル化提案。

**内容:**
- プロジェクトの正しい理解
- 他リポジトリから使いにくい現状の問題点
- シンプル化の具体的提案
  - **examples/ ディレクトリの新設** - コピーして使える構成
  - **ドキュメント構造の整理** - 100+ → 15ファイル
  - **Makefile の簡素化** - 55,311 → <200行
  - **環境変数の整理** - 50+ → サービスごとに5〜10個
  - **Docker Composeの整理** - 各サービスで独立した設定
- 新サービス追加の簡易化
- 実装計画（約1週間で完了）

**対象読者:** プロジェクトオーナー、開発者

**実装優先度:** 🔴 高（すぐに実施すべき）

---

### 🚀 2. [他リポジトリからの利用ガイド](cross-repo-usage-guide.md)

他のリポジトリから各サービスを使う具体的な方法。

**内容:**
- **3つの利用パターン**
  1. Dockerイメージを直接使用（推奨）
  2. 設定ファイルをコピー
  3. Git Submodule
- **サービス別の詳細な使用方法**
  - GitHub MCPサーバー
  - Actions Simulator
  - DateTime Validator
- **実践例とトラブルシューティング**
- **ベストプラクティスとFAQ**

**対象読者:** 他リポジトリでこのツールを使いたい開発者

**実装優先度:** 🟡 中（examples/ 完成後に充実）

---

## 主要な発見

### 定量的データ
| 指標 | 現状 | 問題の深刻度 | 対応方針 |
|------|------|------------|---------|
| ファイル数 | 218 | 🟡 中 | 大幅削減不要（サービス増加予定） |
| コード行数 | 29,000 | 🟡 中 | 適度に保つ |
| **Makefile 行数** | **55,311** | 🔴 極めて高 | **<200行に削減** |
| **ドキュメント数** | **100+** | 🔴 高 | **約15ファイルに削減** |
| **環境変数** | **50+** | 🔴 高 | **サービスごとに5〜10個** |
| テスト/本番比率 | 1.77 | 🟢 良好 | 現状維持 |
| サービス数 | 3 | 🟢 良好 | 今後増加予定 |

### 最重要課題
1. 🔴 **55,311行の Makefile** → <200行に削減
2. 🔴 **100以上のドキュメント** → 約15ファイルに整理
3. 🔴 **examples/ の欠如** → 各サービスの使用例を作成
4. 🔴 **50以上の環境変数** → サービスごとに5〜10個に削減
5. 🟡 **Docker Composeの複雑さ** → サービスごとに独立した設定

---

## 推奨される次のステップ

### 📦 フェーズ1: examples/ 作成（1日）

```
examples/
├── README.md
├── github-mcp/
│   ├── README.md
│   ├── docker-compose.yml
│   ├── .env.example
│   └── config.json.example
├── actions-simulator/
│   ├── README.md
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── run-actions.sh
│   └── Makefile
└── datetime-validator/
    ├── README.md
    ├── docker-compose.yml
    └── .env.example
```

**効果:** 他リポジトリから使いやすくなる

---

### 📝 フェーズ2: ドキュメント整理（2日）

**削除対象:**
- 開発プロセスのレポート（50以上）
- 重複・古いドキュメント

**新構造:**
```
docs/
├── README.md
├── services/
│   ├── github-mcp.md
│   ├── actions-simulator.md
│   └── datetime-validator.md
├── guides/
│   ├── getting-started.md
│   ├── usage-in-other-repos.md
│   └── adding-new-service.md
└── troubleshooting/
    └── common-issues.md
```

**効果:** 情報が見つけやすくなる

---

### 🔧 フェーズ3: Makefile 簡素化（1日）

**目標:** 55,311行 → <200行

**保持するターゲット（約20個）:**
```makefile
# サービス管理
start, stop, restart, logs, status

# 個別サービス
github-mcp, actions, datetime

# 開発
test, lint, format, clean

# ヘルプ
help
```

**効果:** メンテナンスしやすくなる

---

### 🐳 フェーズ4: Docker イメージ公開（1日）

**GitHub Container Registry へ公開:**
- `ghcr.io/your-username/mcp-docker:latest`
- `ghcr.io/your-username/mcp-docker-github:latest`
- `ghcr.io/your-username/mcp-docker-actions:latest`

**効果:** 他リポジトリで `docker pull` だけで使える

---

### ✅ フェーズ5: 検証（1日）

**実施内容:**
1. 実際に他リポジトリで試す
2. 問題点を洗い出し
3. ドキュメント修正
4. README.md 更新

**合計:** 約1週間で完了

---

## 成功指標

### 他リポジトリからの利用
- [ ] 導入時間: <10分
- [ ] 必要ファイル: <3個
- [ ] 環境変数: <5個（サービスごと）
- [ ] `docker compose up` で起動成功

### ドキュメント
- [ ] ファイル数: 100+ → 約15
- [ ] 各サービスの使用方法が1ページで理解可能
- [ ] examples/ を見れば使い方が分かる

### メンテナンス性
- [ ] Makefile: 55,311行 → <200行
- [ ] よく使うコマンド: <20個
- [ ] 新サービス追加: <1時間

### 技術方針の維持
- [ ] Python 3.13+ 継続使用
- [ ] uv 継続使用
- [ ] サービスは柔軟に追加可能
- [ ] 各サービスは独立して使用可能

---

## 関連リソース

### 内部ドキュメント
1. [Dockerサーバー管理のシンプル化](docker-server-management.md) - **メイン提案**
2. [他リポジトリからの利用ガイド](cross-repo-usage-guide.md) - 使用方法

### 外部参考
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [nektos/act](https://github.com/nektos/act) - Actions Simulatorで使用
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP仕様

---

## まとめ

### 実際の目的
- Dockerサーバーをローカルで管理
- 他の自分のリポジトリから簡単に利用
- サービスは今後も増やす（管理はシンプルに）

### 最優先課題
1. **examples/ 作成** - 他リポジトリで使いやすく
2. **ドキュメント整理** - 100+ → 15ファイル
3. **Makefile 簡素化** - 55,311 → <200行
4. **Dockerイメージ公開** - pull して使える

### 実装期間
約1週間で主要な改善を完了可能

### 技術方針
- Python 3.13+ 継続
- uv 継続
- サービス追加を容易に
- 各サービスは独立

---

**分析実施日:** 2025-09-30
**分析バージョン:** 2.0（目的修正版）
**対象プロジェクトバージョン:** 1.2.0
**次回レビュー予定:** フェーズ5完了後
