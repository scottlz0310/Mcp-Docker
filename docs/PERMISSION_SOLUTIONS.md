# Docker権限問題の解決アプローチ

## 🔍 問題の分析

**現在の状況**:
- Dockerコンテナ内: mcpユーザー（UID 1001）
- ホスト: ユーザー（UID 1000）
- 権限不一致によりファイル書き込み失敗

## 🛠️ 解決アプローチ

### 1. UID/GID同期アプローチ（推奨）

**実装方法**:
```bash
# 実行時にホストのUID/GIDを渡す
docker run --user "$(id -u):$(id -g)" -v "$(pwd):/workspace" mcp-docker:latest

# docker-compose.ymlで設定
services:
  datetime-validator:
    user: "${UID:-1000}:${GID:-1000}"
```

**メリット**: セキュリティを保ちつつ権限問題を解決
**デメリット**: 環境変数の管理が必要

### 2. 読み取り専用 + 出力ディレクトリ分離

**実装方法**:
```yaml
services:
  datetime-validator:
    volumes:
      - ~/workspace:/workspace:ro  # 読み取り専用
      - ./output:/output:rw        # 書き込み用
```

**メリット**: セキュリティが高い、権限問題なし
**デメリット**: ファイル修正ではなく報告のみ

### 3. 権限緩和アプローチ（非推奨）

**実装方法**:
```dockerfile
USER root
# または
RUN chmod 777 /workspace
```

**メリット**: 簡単
**デメリット**: セキュリティリスク

## 🎯 推奨実装

### docker-compose.yml修正

```yaml
services:
  datetime-validator:
    build: .
    container_name: mcp-datetime
    user: "${UID:-1000}:${GID:-1000}"
    volumes:
      - ~/workspace:/workspace
    environment:
      - PYTHONPATH=/app
    restart: unless-stopped
    command: python datetime_validator.py --directory /workspace
```

### 環境変数設定

```bash
# .env.template に追加
UID=1000
GID=1000

# 自動設定スクリプト
echo "UID=$(id -u)" >> .env
echo "GID=$(id -g)" >> .env
```

## 🔒 セキュリティ考慮事項

1. **最小権限の原則**: 必要最小限の権限のみ付与
2. **読み取り専用マウント**: 可能な限り:ro使用
3. **UID/GID検証**: 実行時にUID/GIDを確認
4. **ログ監視**: 権限エラーの監視・アラート

## 📝 実装優先度

1. **High**: UID/GID同期（セキュリティ + 機能性）
2. **Medium**: 読み取り専用 + 出力分離（セキュリティ重視）
3. **Low**: 権限緩和（開発環境のみ）
