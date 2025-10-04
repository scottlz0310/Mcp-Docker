# パス解決問題の根本原因と解決策

## 問題の詳細

actが以下のエラーを出力しています：
```
Error: stat /app/.github/workflows/.github/workflows/ci.yml: no such file or directory
```

これは、actが作業ディレクトリを`.github/workflows`に設定し、そこから相対パス`.github/workflows/ci.yml`を解決しようとして、パスが重複することが原因です。

## 根本原因

1. **actの作業ディレクトリ**: `/app/.github/workflows`
2. **指定されたワークフローパス**: `.github/workflows/ci.yml`
3. **結果的なパス**: `/app/.github/workflows/.github/workflows/ci.yml` (重複)

## 解決策

ワークフローファイルを指定する際に、以下のいずれかの方法を使用する：

### 方法1: ファイル名のみを指定
```bash
act -W ci.yml
```

### 方法2: 絶対パスを指定
```bash
act -W /app/.github/workflows/ci.yml
```

### 方法3: 作業ディレクトリをプロジェクトルートに設定
```bash
cd /app && act -W .github/workflows/ci.yml
```

## 実装する解決策

方法1（ファイル名のみ）を採用し、actの作業ディレクトリが`.github/workflows`であることを前提とする。
