# ベストプラクティス

## ワークフロー設計

### バージョン明示

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.13'
```

### キャッシュ活用

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

## ローカル実行

### 基本実行

```bash
act -W .github/workflows/ci.yml
```

### 特定ジョブ

```bash
act -j test
```

### デバッグモード

```bash
act -v -W .github/workflows/ci.yml
```

## CI互換性

### 環境変数統一

```bash
--env-file .env.ci
```

### イメージ固定

```bash
-P ubuntu-latest=ghcr.io/catthehacker/ubuntu:full-22.04
```

### 定期検証

```bash
make verify-ci
```

## パフォーマンス

### リソース制限

```bash
--container-options "--cpus=4 --memory=8g"
```

### キャッシュ永続化

```bash
-v $HOME/.cache/act:/root/.cache
```

### 並列実行

```yaml
strategy:
  matrix:
    python-version: ['3.13']
```

## セキュリティ

### シークレット管理

```bash
act --secret-file .secrets
```

### 権限最小化

```yaml
permissions:
  contents: read
```
