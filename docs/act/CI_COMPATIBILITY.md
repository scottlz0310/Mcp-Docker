# CI互換性ガイド

## 概要

GitHub Actions Simulator（actベース）とGitHub Actions CI環境の互換性ガイド。

## CI互換イメージ

### 使用イメージ（full版）

```bash
-P ubuntu-latest=ghcr.io/catthehacker/ubuntu:full-22.04
-P ubuntu-22.04=ghcr.io/catthehacker/ubuntu:full-22.04
```

### 特徴

- GitHub Actions公式ランナーの完全再現
- 全ツールプリインストール済み
- サイズ: ~18GB

## 環境変数

```bash
CI=true
GITHUB_ACTIONS=true
RUNNER_OS=Linux
RUNNER_ARCH=X64
TZ=UTC
```

## ツールバージョン指定

```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20.x'

- uses: actions/setup-python@v5
  with:
    python-version: '3.13'
```

## 互換性検証

```bash
# デフォルト（basic-test.yml）
make verify-ci

# 特定のワークフロー
./scripts/verify-ci-compatibility.sh .github/workflows/ci.yml

# 特定のCI実行結果を指定
# URL: https://github.com/USER/REPO/actions/runs/18464895672
./scripts/verify-ci-compatibility.sh .github/workflows/basic-test.yml 18464895672
```

## 既知の差異

### 許容される差異
- タイムスタンプ
- ログ出力順序
- 実行時間

### 対処が必要な差異
- ツールバージョン不一致
- 環境変数欠落
- エラーメッセージ形式
