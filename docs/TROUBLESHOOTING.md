# トラブルシューティングガイド

## よくある問題と解決方法

### Docker関連

#### 1. Docker build失敗
```bash
# エラー: permission denied
sudo usermod -aG docker $USER
newgrp docker

# エラー: disk space
docker system prune -a
```

#### 2. サービス起動失敗
```bash
# ポート競合確認
netstat -tulpn | grep :8080

# ログ確認
docker-compose logs [service-name]

# 強制再起動
make clean && make start
```

### GitHub MCP

#### 1. 認証エラー
```bash
# トークン確認
echo $GITHUB_PERSONAL_ACCESS_TOKEN

# 権限確認（repo, read:org必要）
curl -H "Authorization: token $GITHUB_PERSONAL_ACCESS_TOKEN" \
  https://api.github.com/user
```

#### 2. API制限
- レート制限: 5000req/hour
- 制限確認: `X-RateLimit-Remaining` ヘッダー

### DateTime Validator

#### 1. ファイル監視されない
```bash
# 権限確認
ls -la ~/workspace/

# プロセス確認
docker-compose ps datetime

# ログ確認
docker-compose logs datetime
```

#### 2. 日付修正されない
- 対象: `.md`ファイルのみ
- パターン: `2025-01-XX`, `2024-12-XX`
- バックアップ確認: `.bak_*`ファイル

### CI/CD

#### 1. GitHub Actions失敗
```yaml
# ローカル再現
act -j build

# シークレット確認
# Settings > Secrets and variables > Actions
```

#### 2. セキュリティスキャン失敗
```bash
# ローカルTrivy実行
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image mcp-docker:latest
```

## デバッグコマンド

### 基本確認
```bash
# システム情報
docker version
docker-compose version
make --version

# サービス状態
docker-compose ps
docker-compose top

# リソース使用量
docker stats
```

### ログ収集
```bash
# 全ログ
docker-compose logs > debug.log

# 特定サービス
docker-compose logs github > github.log

# リアルタイム
docker-compose logs -f
```

### ネットワーク診断
```bash
# ポート確認
docker-compose port github 8080

# 内部通信テスト
docker-compose exec github ping datetime
```

## パフォーマンス最適化

### メモリ使用量削減
```yaml
# docker-compose.yml
services:
  github:
    mem_limit: 512m
    memswap_limit: 512m
```

### 起動時間短縮
```bash
# イメージキャッシュ活用
docker-compose build --parallel

# 不要コンテナ削除
docker container prune
```

## サポート

### ログ提出時の情報
1. `docker version`
2. `docker-compose version`
3. `docker-compose logs`
4. エラーメッセージ全文
5. 実行環境（OS, アーキテクチャ）

### Issue作成テンプレート
```markdown
## 問題の概要
[簡潔な説明]

## 再現手順
1. [手順1]
2. [手順2]

## 期待する動作
[期待する結果]

## 実際の動作
[実際の結果]

## 環境情報
- OS: [Ubuntu 22.04]
- Docker: [24.0.0]
- Docker Compose: [2.20.0]
```