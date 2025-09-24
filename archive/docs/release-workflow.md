# 🚀 MCP Docker Environment - リリース自動化システム

## 📋 概要

このドキュメントでは、MCP Docker Environmentプロジェクトの次世代リリース自動化システムについて詳しく説明します。本システムは完全自動化されたCI/CDパイプラインにより、開発からリリースまでの全工程を統合的に管理します。

## 🎯 システム特徴

### 🔥 完全自動化機能

- **🚀 ワンクリックリリース**: GitHub Actions UIから完全自動実行
- **🔄 スマートバージョン管理**: pyproject.toml ↔ main.py 自動同期
- **📝 インテリジェントCHANGELOG**: Git履歴からConventional Commits解析
- **🏗️ 統合ドキュメント**: Sphinx + GitHub Pages自動デプロイ
- **🛡️ セキュリティ保証**: バージョン後退禁止・権限管理

### 🎛️ 多様なトリガー

- **手動実行** (`workflow_dispatch`): GitHub Actions UI
- **タグプッシュ** (`push: tags`): `git tag v1.0.0 && git push origin v1.0.0`
- **ドキュメント連動** (`repository_dispatch`): リリース時自動更新

### 🧠 インテリジェント処理

- **バージョン整合性チェック**: 自動検証・同期
- **品質保証統合**: CI/CDテスト完全連携
- **変更履歴自動分類**: 機能・修正・ドキュメント・その他
- **リリースノート生成**: CHANGELOG抽出・GitHub Release統合

## 🔄 完全自動化フローチャート

```mermaid
flowchart TD
    A[👨‍💻 開発者] --> B{🎯 リリース方式選択}

    B -->|手動実行| C[🖱️ GitHub Actions UI<br/>バージョン指定]
    B -->|タグプッシュ| D[📎 git tag v1.0.0<br/>git push origin v1.0.0]

    C --> E[🔥 workflow_dispatch]
    D --> F[🏷️ push tags]

    E --> G[🔍 version-check]
    F --> G

    G --> H[📊 バージョン情報抽出]
    H --> I[🧠 スマートバージョンチェック]
    I --> J{⚖️ バージョン比較}

    J -->|現在 > 指定| K[❌ エラー終了<br/>バージョン後退禁止]
    J -->|現在 = 指定| L[🔄 quality-check]
    J -->|現在 < 指定| M[⬆️ 自動バージョン更新<br/>pyproject.toml + main.py]

    M --> L
    L --> N[🧪 CI/CDテスト実行<br/>全品質チェック]
    N --> O[📝 prepare-release]

    O --> P[📚 CHANGELOG自動生成<br/>Conventional Commits解析]
    P --> Q[📄 リリースノート生成]
    Q --> R{🔄 変更検出?}

    R -->|Yes| S[💾 自動コミット・プッシュ]
    R -->|No| T[🚀 create-release]
    S --> T

    T --> U[📦 パッケージビルド]
    U --> V{🎯 トリガー判定}

    V -->|手動実行| W[🏷️ タグ作成・プッシュ]
    V -->|タグプッシュ| X[🎉 GitHub Release作成]
    W --> X

    X --> Y[📚 update-docs<br/>repository_dispatch]
    Y --> Z[📊 post-release<br/>メトリクス記録]

    Z --> AA[🎊 リリース完了]

    style A fill:#e1f5fe
    style B fill:#fff3e0
    style G fill:#f3e5f5
    style I fill:#e8f5e8
    style J fill:#fff3e0
    style K fill:#ffebee
    style L fill:#f3e5f5
    style O fill:#e8f5e8
    style T fill:#fff3e0
    style AA fill:#e8f5e8
```

## 🚀 手動リリース実行（推奨方式）

### 📋 実行手順

1. **🌐 GitHub Actions画面**へ移動
   ```
   https://github.com/scottlz0310/Mcp-Docker/actions
   ```

2. **🎯 ワークフロー選択**
   - **「🚀 Release Management」**を選択

3. **▶️ ワークフロー実行**
   - **「Run workflow」**ボタンをクリック

4. **📝 パラメータ設定**
   - **`version`**: 新しいバージョン (例: `1.3.7`, `2.0.0`)
   - **`prerelease`**: プレリリースフラグ (`true`/`false`)

5. **🚀 実行開始**
   - **「Run workflow」**で自動化開始

### 🎢 処理シーケンス
    V -->|Yes| W[タグ作成・プッシュ]
    V -->|No| X[GitHub Release作成]
    W --> X

    X --> Y[アセット添付]
    Y --> Z[post-release ジョブ]
    Z --> AA[リリースメトリクス記録]
    AA --> BB[🎉 リリース完了]
```

## 🚀 手動リリース（推奨）

### 使用方法

1. **GitHub Actions画面**に移動
2. **🚀 Release Management**ワークフローを選択
3. **「Run workflow」**をクリック
4. **パラメータ入力**:
   - `version`: リリースバージョン (例: 1.3.6)
   - `prerelease`: プレリリースフラグ (true/false)
5. **「Run workflow」**で実行

### 処理フロー

```mermaid
sequenceDiagram
    participant Dev as 開発者
    participant GH as GitHub Actions
    participant Repo as リポジトリ

    Dev->>GH: バージョン指定で実行
    GH->>Repo: スマートバージョンチェック

    alt 現在 > 指定
        GH->>Dev: ❌ エラー: バージョンの後退禁止
    else 現在 < 指定
        GH->>Repo: 自動バージョン更新
    end

    GH->>Repo: Git履歴からCHANGELOG生成
    GH->>Repo: リリースノート生成

    alt 変更あり
        GH->>Repo: 自動コミット・プッシュ
    end

    GH->>Repo: タグ作成・プッシュ
    GH->>GH: GitHub Release作成
    GH->>Dev: 🎉 リリース完了通知
```

## 🏷️ タグプッシュリリース

### 使用方法

```bash
# ローカルでタグ作成・プッシュ
git tag v1.3.6
git push origin v1.3.6
```

### 処理フロー

```mermaid
sequenceDiagram
    participant Dev as 開発者
    participant GH as GitHub Actions
    participant Repo as リポジトリ

    Dev->>Repo: git tag v1.3.6 && git push origin v1.3.6
    Repo->>GH: タグプッシュトリガー
    GH->>Repo: スマートバージョンチェック

    alt 現在 < タグバージョン
        GH->>Repo: 自動バージョン更新
    end

    GH->>Repo: Git履歴からCHANGELOG生成
    GH->>Repo: リリースノート生成

    alt 変更あり
        GH->>Repo: 自動コミット・プッシュ
    end

    Note over GH: タグ作成はスキップ（既存）
    GH->>GH: GitHub Release作成
    GH->>Dev: 🎉 リリース完了通知
```

## 🔧 ジョブ詳細

### 1. version-check ジョブ

**目的**: スマートバージョンチェックと自動更新

**処理内容**:
- トリガー種別の判定（手動 or タグプッシュ）
- バージョン情報の抽出
- プレリリースフラグの判定
- **スマートバージョンチェック**:
  - 現在 > 指定: エラーで終了
  - 現在 = 指定: 継続
  - 現在 < 指定: 自動更新

**出力**:
- `version`: 対象バージョン
- `is-prerelease`: プレリリースフラグ

### 2. quality-check ジョブ

**目的**: コード品質とテストの実行

**処理内容**:
- CI/CDワークフロー（ci.yml）の実行
- リンティング、型チェック、テスト実行
- セキュリティスキャン

### 3. prepare-release ジョブ

**目的**: リリース準備とドキュメント生成

**処理内容**:
1. **CHANGELOG自動生成・更新**
   - Git履歴からConventional Commitsを解析
   - カテゴリ別に変更内容を分類
   - 既存エントリがあれば日付のみ更新
2. **リリースノート生成**
   - CHANGELOGから該当バージョンを抽出
   - GitHub Release用のマークダウン生成
3. **自動コミット**
   - 変更があれば自動コミット・プッシュ

> **注意**: バージョン更新はversion-checkジョブで完了済み

**出力**:
- `changes-made`: 変更有無フラグ

### 4. create-release ジョブ

**目的**: タグ作成とGitHub Release作成

**処理内容**:
1. **パッケージビルド**
   - Python wheelとtarballの生成
2. **タグ作成（条件付き）**
   - 手動実行時のみタグ作成・プッシュ
   - タグプッシュ時はスキップ
3. **GitHub Release作成**
   - リリースノートを使用
   - アセット添付（dist/, CHANGELOG.md, README.md, LICENSE）

### 5. post-release ジョブ

**目的**: リリース後処理とメトリクス記録

**処理内容**:
- リリースメトリクスの記録
- 成功通知

## 🤖 スマートバージョンチェック

### バージョン比較ロジック

リリースワークフローの最初に実行されるスマートチェック機能：

```mermaid
flowchart TD
    A[スマートバージョンチェック] --> B{バージョン比較}

    B -->|現在 > 指定| C[❌ エラーで終了]
    B -->|現在 = 指定| D[✅ 継続]
    B -->|現在 < 指定| E[🔄 自動更新]

    C --> F[🚨 バージョン後退禁止]
    E --> G[✅ 継続]
    D --> H[✅ 継続]
    G --> H
```

### 具体例

| 現在バージョン | 指定バージョン | 動作 | 結果 |
|---|---|---|---|
| 1.3.5 | 1.4.0 | 自動更新 | ✅ 1.3.5 → 1.4.0 |
| 1.4.0 | 1.4.0 | 継続 | ✅ 更新不要 |
| 1.5.0 | 1.4.0 | エラー | ❌ バージョン後退禁止 |
| 2.0.0 | 1.9.0 | エラー | ❌ バージョン後退禁止 |

### セキュリティ機能

- **バージョン後退禁止**: セキュリティ上の理由でダウングレードを禁止
- **自動アップグレード**: 安全なバージョンアップのみ許可
- **一貫性保証**: pyproject.tomlと__init__.pyの同期更新

## 🤖 自動CHANGELOG生成

### Conventional Commits対応

以下のコミット形式を自動認識：

- `feat:` → ✨ 新機能
- `fix:` → 🐛 修正
- `docs:` → 📝 ドキュメント
- `refactor:` → 🔄 変更
- その他 → 🔧 その他

### 生成例

```markdown
## [1.3.6] - 2025-09-24

### ✨ 新機能
- 完全自動化リリースフロー実装
- Git履歴ベースのCHANGELOG生成

### 🐛 修正
- YAML構文エラー修正
- バージョン整合性チェック改善

### 🔄 変更
- リリースワークフローの最適化
- ドキュメント構造の改善
```

## 🎯 使い分けガイド

### 手動リリース（推奨）

**適用場面**:
- 定期リリース
- 機能リリース
- 緊急修正リリース

**メリット**:
- CI画面で簡単実行
- バージョン指定が明確
- プレリリースフラグ制御可能

### タグプッシュリリース

**適用場面**:
- ローカル開発環境からのリリース
- スクリプト自動化
- 既存ワークフローとの連携

**メリット**:
- コマンドライン完結
- 既存のGitワークフローと統合
- 自動化スクリプトに組み込み可能

## 🔍 トラブルシューティング

### よくある問題

1. **「Run workflow」ボタンが表示されない**
   - YAML構文エラーの可能性
   - mainブランチにプッシュされているか確認

2. **バージョン後退エラー**
   - 現在のバージョンが指定バージョンより進んでいる
   - 解決: 指定バージョンを現在より大きくする
   - 例: 現在 1.5.0 → 指定 1.6.0 以上

3. **バージョン整合性エラー**
   - スマートチェック機能により自動解決
   - 手動修正が必要な場合はログを確認

3. **CHANGELOG生成が空**
   - Git履歴にConventional Commitsがない
   - フォールバック機能により最小限の内容を生成

4. **タグが重複**
   - 既存タグの確認
   - 手動削除後に再実行

### デバッグ方法

1. **ワークフローログの確認**
   - GitHub Actions画面でログ詳細を確認
   - 各ジョブの実行結果をチェック

2. **ローカルでのテスト**
   ```bash
   # バージョン管理スクリプトのテスト
   uv run python scripts/version-manager.py --check
   uv run python scripts/version-manager.py --smart-check 1.3.6
   uv run python scripts/version-manager.py --update-changelog 1.3.6
   ```

3. **YAML構文チェック**
   ```bash
   # ローカルでYAML構文確認
   uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"
   ```

## 📚 関連ドキュメント

- [バージョン管理ガイド](version-management.md)
- [CI/CDパイプライン](ci-cd-pipeline.md)
- [開発者ガイド](../README.md#開発・テスト)
- [品質管理システム](quality-management.md)
