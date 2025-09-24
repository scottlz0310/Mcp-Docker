# GitHub Actions Simulator - 新規サービス提案書

## 🔄 設計変更の理由

### ❌ 当初の問題
- CodeQLは静的コード分析ツール
- GitHub Actions Simulatorは動的CI実行ツール
- 役割が明確に異なるため混在は不適切

### ✅ 新しいアプローチ：独立サービス `actions`

現在の既存構成：
```
services/
├── github/       # GitHub MCP Server
├── datetime/     # DateTime Validator
├── codeql/       # CodeQL Analysis（静的解析）
└── actions/      # 🆕 GitHub Actions Simulator（動的CI実行）
```

## 🎯 新規サービス `actions` の設計

### サービス統合パターン

既存の3サービスと同じパターンを踏襲：

```python
# main.py 拡張（既存パターン）
if service == "github":
    cmd = ["python", "-m", "mcp_server_github"]
elif service == "datetime":
    cmd = ["python", "services/datetime/datetime_validator.py"]
elif service == "codeql":
    print("CodeQL analysis not implemented yet")
elif service == "actions":  # 🆕 追加
    from services.actions.cli import actions_cli
    sys.argv = ["actions"] + sys.argv[2:]
    actions_cli()
```

### 使用方法の統一性

```bash
# 既存サービスと同じパターン
python main.py github    # GitHub MCP Server
python main.py datetime  # DateTime Validator
python main.py codeql    # CodeQL Analysis
python main.py actions simulate ci.yml  # 🆕 Actions Simulator

# Makefileターゲットも統一
make github     # GitHub MCP起動
make datetime   # DateTime Validator起動
make codeql     # CodeQL実行
make actions    # 🆕 Actions Simulator起動
```

## 🏗️ 技術アーキテクチャ

### act統合によるメリット

1. **成熟したエコシステム**: 40,000+ stars、実戦実績
2. **高い互換性**: GitHub Actions 90%以上対応
3. **豊富なランナー**: Ubuntu各バージョン、Node.js等
4. **アクティブ開発**: 継続的なアップデート・バグ修正

### 実装構成

```
services/actions/
├── cli.py              # Click ベースCLI
├── act_wrapper.py      # act binary統合
├── config.yml          # サービス設定
├── workflow_parser.py  # YAML解析・検証
├── report_generator.py # 実行結果レポート
└── models/
    ├── workflow.py     # ワークフローモデル
    └── execution.py    # 実行状態モデル
```

## 🚀 想定される使用例

### 1. 基本的なワークフロー実行
```bash
# 既存のci.ymlをローカル実行
python main.py actions simulate .github/workflows/ci.yml

# 特定イベントでのテスト
python main.py actions simulate ci.yml --event pull_request

# 特定ジョブのみ実行（高速フィードバック）
python main.py actions simulate ci.yml --job test
```

### 2. 開発ワークフロー統合
```bash
# Git commit前の事前チェック
git add . && python main.py actions simulate ci.yml && git commit

# プルリクエスト前の事前確認
python main.py actions simulate ci.yml --event pull_request
```

### 3. CI/CD最適化
```bash
# ワークフロー検証
python main.py actions validate .github/workflows/ci.yml

# パフォーマンス分析
python main.py actions simulate ci.yml --output-format html --report perf.html
```

## 💻 Docker統合

### 既存のDocker環境活用

```dockerfile
# Dockerfile（act binary追加）
# 既存のマルチステージビルドに追加
RUN curl -L -o /tmp/act.tar.gz \
    "https://github.com/nektos/act/releases/latest/download/act_Linux_x86_64.tar.gz" && \
    tar -xzf /tmp/act.tar.gz -C /usr/local/bin act && \
    chmod +x /usr/local/bin/act
```

```yaml
# docker-compose.yml（新サービス追加）
services:
  # 既存サービス継続...

  actions-simulator:
    build: .
    container_name: mcp-actions
    volumes:
      - ./.github:/app/.github:ro
      - /var/run/docker.sock:/var/run/docker.sock
    command: python main.py actions --help
    networks:
      - mcp-network
```

## 📋 実装計画

### Phase 1: MVP（1週間）
- [ ] `services/actions/` 基本構造作成
- [ ] act binary統合・動作確認
- [ ] 基本CLI（simulate コマンド）
- [ ] 既存ci.ymlでの動作テスト

### Phase 2: 機能拡張（2週間）
- [ ] 高度なオプション（--job, --event等）
- [ ] 設定ファイル統合
- [ ] レポート生成機能
- [ ] エラーハンドリング

### Phase 3: 統合・仕上げ（1週間）
- [ ] 既存テストスイート統合
- [ ] Makefileターゲット追加
- [ ] ドキュメント更新
- [ ] リリース準備

## 🔐 セキュリティ考慮

### コンテナセキュリティ
- Docker socket アクセス制限
- 非rootユーザーでの実行
- リソース制限（CPU、メモリ）
- ネットワーク隔離

### シークレット管理
- ローカルファイル暗号化
- 環境変数経由での注入
- ログ自動マスキング

## 📊 期待効果

### 開発効率向上
- **CI実行前検証**: ローカル環境での事前確認
- **高速フィードバック**: GitHub Actions待機時間削減
- **デバッグ効率**: ローカルでの詳細調査可能

### コスト削減
- **GitHub Actions使用料**: 失敗回数減少により削減
- **開発時間**: エラー発見・修正サイクル短縮

### 品質向上
- **CI設定の信頼性**: 本番環境前の検証
- **ワークフロー最適化**: パフォーマンス分析・改善

## 🎯 次のステップ

### 1. プロトタイプ作成
```bash
# 基本ディレクトリ作成
mkdir -p services/actions
touch services/actions/{cli.py,act_wrapper.py,config.yml}

# act バイナリ動作確認
act --version
act -W .github/workflows/ci.yml --dry-run
```

### 2. 段階的統合
1. まずact単体での動作確認
2. Python wrapperの作成
3. main.py統合
4. docker-compose統合

### 3. テスト・検証
1. 既存ワークフローでの動作確認
2. パフォーマンス測定
3. セキュリティ検証

## 🎉 まとめ

**新規独立サービス `actions`** のアプローチは以下の理由で最適です：

1. **責任分離**: 各サービスが明確な役割を持つ
2. **既存パターン継承**: 学習コスト・実装コスト最小化
3. **技術的優位性**: act のエコシステム活用
4. **拡張性**: 将来的な機能追加に対応

このアプローチで実装を進めることで、既存のMcp-Dockerプロジェクトの価値を最大限に活用しつつ、実用的なGitHub Actions Simulatorを効率的に構築できます。
