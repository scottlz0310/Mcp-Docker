# トラブルシューティングガイド

## 概要

MCP Docker環境で発生する一般的な問題と解決方法を説明します。

## 一般的な問題

### Docker関連の問題

#### Docker権限エラー
```bash
# 解決方法
sudo usermod -aG docker $USER
newgrp docker
```

#### コンテナ起動失敗
```bash
# ログ確認
docker logs <container_name>

# 権限確認
ls -la /var/run/docker.sock
```

### GitHub Actions関連の問題

#### 認証エラー
- GitHub Personal Access Tokenの権限を確認
- 必要な権限: `repo`, `workflow`, `actions:read`

#### ワークフロー実行失敗
- ログを確認してエラーの詳細を特定
- 依存関係の問題がないか確認

### MCP サーバー関連の問題

#### サーバー接続失敗
```bash
# 環境変数確認
echo $GITHUB_PERSONAL_ACCESS_TOKEN

# コンテナ状態確認
docker ps -a
```

## サポート

問題が解決しない場合は、以下の情報を含めてIssueを作成してください：

- エラーメッセージ
- 実行環境（OS、Dockerバージョン）
- 実行したコマンド
- ログファイル

詳細は[SUPPORT.md](SUPPORT.md)を参照してください。
