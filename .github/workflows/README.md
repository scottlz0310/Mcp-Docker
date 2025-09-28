# GitHub Actions Simulator - ワークフローテンプレート

このディレクトリには、GitHub Actions Simulator で使用するためのワークフローテンプレートが含まれています。これらのテンプレートは軽量なactベースアーキテクチャに最適化されており、ローカル環境での高速実行を重視しています。

## 📋 利用可能なテンプレート

### 1. local-ci.yml.sample - 包括的なCIパイプライン

**用途**: 本格的なCI/CDパイプラインのテンプレート
**実行時間**: 15-30分
**含まれる機能**:
- 高速リント・基本チェック
- Dockerイメージビルド
- 単体テスト（pytest）
- 統合テスト（Docker Compose）
- セキュリティスキャン（Trivy、TruffleHog）
- パフォーマンステスト（オプション）
- 結果サマリー・レポート生成

```bash
# 使用例
make actions-run WORKFLOW=.github/workflows/local-ci.yml
```

### 2. basic-test.yml.sample - 軽量テストパイプライン

**用途**: 高速なプルリクエストチェック
**実行時間**: 5-10分
**含まれる機能**:
- Python静的解析（Ruff）
- 単体テスト（pytest）
- 基本的なコード品質チェック

```bash
# 使用例
make actions-run WORKFLOW=.github/workflows/basic-test.yml
```

### 3. security-scan.yml.sample - セキュリティ特化パイプライン

**用途**: 包括的なセキュリティチェック
**実行時間**: 10-20分
**含まれる機能**:
- ファイルシステム脆弱性スキャン（Trivy）
- 依存関係脆弱性チェック（pip-audit、npm audit）
- Dockerイメージ脆弱性スキャン
- 秘密情報スキャン（TruffleHog）
- セキュリティレポート生成

```bash
# 使用例
make actions-run WORKFLOW=.github/workflows/security-scan.yml
```

## 🚀 クイックスタート

### 1. テンプレートのコピー

```bash
# 包括的なCIパイプラインを使用する場合
cp .github/workflows/local-ci.yml.sample .github/workflows/local-ci.yml

# 軽量テストのみの場合
cp .github/workflows/basic-test.yml.sample .github/workflows/basic-test.yml

# セキュリティスキャンのみの場合
cp .github/workflows/security-scan.yml.sample .github/workflows/security-scan.yml
```

### 2. プロジェクトに合わせてカスタマイズ

各テンプレートファイル内のコメントを参考に、以下の項目を調整してください：

- **Python バージョン**: `PYTHON_VERSION` 環境変数
- **テストコマンド**: pytest の引数やオプション
- **Docker 設定**: イメージ名、ビルド引数
- **セキュリティ設定**: Trivy の重要度レベル、無視する脆弱性

### 3. GitHub Actions Simulator で実行

```bash
# インタラクティブ実行
make actions

# 特定のワークフローを実行
make actions-run WORKFLOW=.github/workflows/local-ci.yml

# 特定のジョブのみ実行
make actions-run WORKFLOW=.github/workflows/local-ci.yml JOB=unit-tests

# 詳細ログ付きで実行
make actions-run WORKFLOW=.github/workflows/local-ci.yml VERBOSE=1
```

## ⚙️ カスタマイズガイド

### 環境変数の設定

各テンプレートで使用される主要な環境変数：

```yaml
env:
  # Python設定
  PYTHON_VERSION: '3.13'          # 使用するPythonバージョン
  PYTHONUNBUFFERED: 1             # Python出力バッファリング無効化

  # uv設定
  UV_CACHE_DIR: /tmp/.uv-cache    # uvキャッシュディレクトリ

  # Docker設定
  DOCKER_BUILDKIT: 1              # BuildKit有効化
  COMPOSE_DOCKER_CLI_BUILD: 1     # Docker Compose CLI Build有効化

  # テスト設定
  TEST_MODE: true                 # テストモード有効化
  PYTEST_TIMEOUT: 300             # pytestタイムアウト（秒）

  # セキュリティ設定
  SECURITY_SCAN_ENABLED: true     # セキュリティスキャン有効化
```

### ジョブの有効化/無効化

不要なジョブを無効化する方法：

```yaml
# 条件付きでジョブを無効化
integration-tests:
  if: ${{ github.event.inputs.run_integration_tests != 'false' }}
  # ...

# 特定の条件でのみ実行
performance-test:
  if: ${{ github.event_name == 'workflow_dispatch' }}
  # ...

# 依存関係から除外
summary:
  needs: [fast-checks, build, unit-tests]  # integration-testsを除外
  # ...
```

### テストコマンドのカスタマイズ

pytest の設定例：

```yaml
- name: 🧪 pytest実行
  run: |
    uv run pytest \
      --verbose \
      --tb=short \
      --cov=src \                    # カバレッジ対象ディレクトリ
      --cov-report=xml \
      --cov-report=term-missing \
      --junit-xml=test-results.xml \
      --maxfail=5 \                  # 最大失敗数
      --timeout=300 \                # テストタイムアウト
      tests/                         # テストディレクトリ
```

### Docker設定のカスタマイズ

Dockerビルドの設定例：

```yaml
- name: 🔨 Dockerイメージビルド
  uses: docker/build-push-action@v5
  with:
    context: .
    platforms: linux/amd64,linux/arm64  # マルチプラットフォーム
    tags: |
      myapp:latest
      myapp:${{ github.sha }}
    build-args: |
      PYTHON_VERSION=${{ env.PYTHON_VERSION }}
      BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    cache-from: type=gha              # GitHub Actions キャッシュ
    cache-to: type=gha,mode=max
```

### セキュリティスキャンの設定

Trivy の設定例：

```yaml
- name: 🔍 脆弱性スキャン
  uses: aquasecurity/trivy-action@0.33.1
  with:
    scan-type: 'fs'
    format: 'sarif'
    severity: 'CRITICAL,HIGH,MEDIUM'   # スキャン重要度
    exit-code: '1'                     # 脆弱性検出時の終了コード
    trivyignores: '.trivyignore'       # 無視する脆弱性の設定ファイル
    ignore-unfixed: true               # 修正不可能な脆弱性を無視
```

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. Docker権限エラー

```bash
# 解決方法
./scripts/fix-permissions.sh
make docker-health
```

#### 2. uv インストールエラー

```yaml
# フォールバック戦略を追加
- name: ⚡ uv インストール
  run: |
    curl -LsSf https://astral.sh/uv/install.sh | sh || {
      echo "⚠️ uv installation failed, using pip fallback"
      python -m pip install --upgrade pip
    }
```

#### 3. テストタイムアウト

```yaml
# タイムアウト時間を延長
env:
  PYTEST_TIMEOUT: 600  # 10分に延長
```

#### 4. メモリ不足エラー

```yaml
# Docker リソース制限を調整
services:
  test-db:
    image: postgres:15
    options: >-
      --memory=512m
      --cpus=1.0
```

### デバッグ方法

#### 詳細ログの有効化

```bash
# 詳細ログ付きで実行
make actions-run WORKFLOW=.github/workflows/local-ci.yml VERBOSE=1

# 環境変数でデバッグモードを有効化
ACTIONS_SIMULATOR_DEBUG=true make actions
```

#### ステップバイステップ実行

```bash
# 特定のジョブのみ実行
make actions-run WORKFLOW=.github/workflows/local-ci.yml JOB=fast-checks

# 失敗したジョブを再実行
make actions-run WORKFLOW=.github/workflows/local-ci.yml JOB=unit-tests
```

## 📚 関連ドキュメント

- [GitHub Actions Simulator ユーザーガイド](../../docs/actions/USER_GUIDE.md)
- [トラブルシューティングガイド](../../docs/TROUBLESHOOTING.md)
- [セキュリティガイド](../../docs/SECURITY.md)
- [API リファレンス](../../docs/API_REFERENCE.md)

## 🤝 コントリビューション

ワークフローテンプレートの改善提案や新しいテンプレートの追加は、以下の手順で行ってください：

1. 新しいテンプレートファイルを作成（`.sample` 拡張子付き）
2. 詳細なコメントと使用例を追加
3. このREADMEファイルにテンプレートの説明を追加
4. テンプレートの動作確認を実施
5. プルリクエストを作成

## 📄 ライセンス

これらのテンプレートは、プロジェクトのライセンスに従って自由に使用・改変できます。
