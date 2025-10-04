# パス解決問題の最終解決策

## 現状の問題

actが以下のエラーを出力：
```
Error: stat /app/.github/workflows/.github/workflows/ci.yml: no such file or directory
```

## 根本原因

actは作業ディレクトリを`.github/workflows`に設定し、そこから相対パス`.github/workflows/ci.yml`を解決しようとして、パスが重複する。

## 最終解決策

### 方法1: 作業ディレクトリをプロジェクトルートに固定
actの実行時に、作業ディレクトリを明示的にプロジェクトルート（`/app`）に設定し、ワークフローファイルは相対パス（`.github/workflows/ci.yml`）で指定する。

### 方法2: 絶対パスを使用
ワークフローファイルを絶対パス（`/app/.github/workflows/ci.yml`）で指定する。

## 実装

方法2（絶対パス）を採用し、確実にパス重複を回避する。
