# ワークフロー例（Examples）

このディレクトリには、GitHub Actionsワークフローのサンプル設定が含まれています。

## ファイル一覧

### basic-ci-example.yml
基本的なCI設定の例。以下を含みます：
- Lint（ruff, shellcheck等）
- ユニットテスト
- Dockerビルド

**用途**: シンプルなプロジェクト向けのCI設定

### comprehensive-tests.yml
包括的なテスト設定の例。以下を含みます：
- ユニットテスト
- 統合テスト
- E2Eテスト
- セキュリティスキャン

**用途**: 大規模プロジェクト向けの完全なテストパイプライン

### docs-validation.yml
ドキュメント検証設定の例。以下を含みます：
- Markdownリンク検証
- ドキュメント整合性チェック
- スペルチェック

**用途**: ドキュメント重視のプロジェクト

### local-development-ci.yml
ローカル開発環境でのCI設定例（nektos/act用）。

**用途**: ローカルでGitHub Actionsを実行する場合

### security-scanning.yml
セキュリティスキャン設定の例。以下を含みます：
- Bandit（Python）
- Trivy（コンテナ）
- CodeQL
- 依存関係チェック

**用途**: セキュリティ重視のプロジェクト

## 使い方

### 1. 必要なファイルをコピー

```bash
# 基本的なCI設定をコピー
cp docs/examples/workflows/basic-ci-example.yml .github/workflows/ci.yml
```

### 2. プロジェクトに合わせてカスタマイズ

- ブランチ名を調整
- テストコマンドを修正
- 不要なステップを削除

### 3. プッシュして動作確認

```bash
git add .github/workflows/ci.yml
git commit -m "ci: GitHub Actionsワークフローを追加"
git push
```

## 本番環境のワークフロー

実際に使用されているワークフローは `.github/workflows/` ディレクトリにあります：

- **ci.yml** - メインCI（PR・mainブランチpush時）
- **security.yml** - セキュリティスキャン
- **release.yml** - リリース自動化
- **dependabot-auto-merge.yml** - Dependabot自動マージ

## カスタマイズのヒント

### 実行時間の最適化

```yaml
# キャッシュを活用
- uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-uv-${{ hashFiles('**/pyproject.toml') }}

# 並列実行を活用
strategy:
  matrix:
    python-version: ['3.11', '3.12', '3.13']
```

### 条件付き実行

```yaml
# mainブランチのみ実行
if: github.ref == 'refs/heads/main'

# PRのみ実行
if: github.event_name == 'pull_request'
```

## 参考リンク

- [GitHub Actions ドキュメント](https://docs.github.com/ja/actions)
- [ワークフロー構文](https://docs.github.com/ja/actions/using-workflows/workflow-syntax-for-github-actions)
- [nektos/act（ローカル実行）](https://github.com/nektos/act)
