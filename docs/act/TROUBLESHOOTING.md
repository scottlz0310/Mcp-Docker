# トラブルシューティング

## イメージ関連

### イメージpull失敗

```bash
docker pull ghcr.io/catthehacker/ubuntu:full-22.04
```

### ディスク容量不足

```bash
docker system prune -a
```

## 実行エラー

### Docker接続エラー

```bash
sudo systemctl start docker
```

### 権限エラー

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## ツールバージョン不一致

### バージョン確認

```bash
act -j test --env ACTIONS_STEP_DEBUG=true
```

### setup-actions追加

```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20.x'
```

## キャッシュ問題

### キャッシュクリア

```bash
docker volume prune
```

### ボリュームマウント

```bash
act -v $HOME/.cache/act:/root/.cache
```

## ログ差異

### 詳細ログ有効化

```bash
act -v -W .github/workflows/ci.yml
```

### JSON出力

```bash
act --json > output.json
```
