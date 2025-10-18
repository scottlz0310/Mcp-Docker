# GitHub Actions ローカル実行 - クイックスタート

## 📦 インストール

```bash
# 1. actをインストール
brew install act

# 2. mcp-dockerをインストール
uv tool install git+https://github.com/scottlz0310/mcp-docker.git

# 3. Dockerイメージを事前にプル（推奨）
# full版は18GB、初回実行が遅いため事前プルを推奨
docker pull ghcr.io/catthehacker/ubuntu:full-24.04
```

### イメージサイズ比較

| イメージ | サイズ | 用途 |
|---------|--------|------|
| `ghcr.io/catthehacker/ubuntu:full-24.04` | ~18GB | 完全互換（推奨） |
| `ghcr.io/catthehacker/ubuntu:act-24.04` | ~8GB | 軽量版 |
| `ubuntu:latest` | ~80MB | 最小構成 |

```bash
# 軽量版を使う場合（.actrcで設定）
echo "-P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-24.04" > .actrc
```

## 🚀 使い方

### 基本的な使い方

```bash
# ワークフローを実行
mcp-docker actions .github/workflows/ci.yml

# ワークフロー一覧を表示
mcp-docker actions .github/workflows/ci.yml --list

# 特定のジョブのみ実行
mcp-docker actions .github/workflows/ci.yml --job test
```

### 実行例

```bash
$ mcp-docker actions .github/workflows/basic-test.yml

🚀 .github/workflows/basic-test.yml を実行中...

[Basic Test Pipeline/🧪 基本テスト] ⭐ Run Set up job
[Basic Test Pipeline/🧪 基本テスト] ✅ Success - Set up job
...

✅ 成功 (19.2秒)
📝 ログ: logs/actions.log
```

### 失敗時の自動解析

エラーが発生すると、自動的に原因を解析して解決策を提示します:

```bash
$ mcp-docker actions .github/workflows/ci.yml

🚀 .github/workflows/ci.yml を実行中...
...
❌ 失敗 (終了コード: 1)

🔍 失敗原因を解析中...

📊 ログ解析結果
==================================================
❌ ステータス: 失敗
⏱️  実行時間: 19.0秒

🔴 エラー:
  1. 失敗したステップ: 🔍 コード品質チェック (Ruff)
  2. エラー: src/file.py:10:5: F401 imported but unused

💡 解決策:
  • コードフォーマット: uv run ruff format .
  • コード修正: uv run ruff check --fix .

📝 ログ: logs/actions.log
```

## 📝 ログ

すべての実行ログは `logs/actions.log` に保存されます。

```bash
# ログを確認
cat logs/actions.log

# 最新の実行結果のみ表示
tail -50 logs/actions.log
```

## 💡 Tips

### よく使うオプション

```bash
# ドライラン（実際には実行しない）
mcp-docker actions .github/workflows/ci.yml --dryrun

# 特定のイベントで実行
mcp-docker actions .github/workflows/ci.yml --eventpath event.json

# 環境変数を設定
mcp-docker actions .github/workflows/ci.yml --env KEY=VALUE
```

### トラブルシューティング

**Q: actがインストールされていないと言われる**
```bash
# actをインストール
brew install act
```

**Q: Dockerエラーが出る**
```bash
# Docker Desktopが起動しているか確認
docker ps
```

**Q: 初回実行が非常に遅い**
```bash
# Dockerイメージを事前にプル（18GBのダウンロード）
docker pull ghcr.io/catthehacker/ubuntu:full-24.04

# または軽量版を使用（8GB）
echo "-P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-24.04" > .actrc
docker pull ghcr.io/catthehacker/ubuntu:act-24.04
```

**Q: 2回目以降も遅い**
```bash
# キャッシュをクリア
rm -rf ~/.cache/act
```

## 🔗 関連リンク

- [act公式ドキュメント](https://github.com/nektos/act)
- [GitHub Actions公式ドキュメント](https://docs.github.com/actions)
