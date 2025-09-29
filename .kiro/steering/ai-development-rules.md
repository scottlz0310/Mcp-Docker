# AI開発支援ルール

## 🤖 AI開発者への指示

このファイルは、AI開発支援システム（Kiro等）が本プロジェクトで作業する際の**絶対遵守事項**です。

## 🚫 絶対禁止事項

### Python実行コマンド
- **絶対に使用禁止**: `python3`, `python`, `pip`, `python -m pip`
- **理由**: 本プロジェクトはuvによる依存関係管理を採用
- **違反時の対応**: コマンド実行前に必ず`uv run`プレフィックスを付ける

### パッケージ管理
- **絶対に使用禁止**: `apt`, `apt-get`, `yum`, `dnf`
- **理由**: クロスプラットフォーム対応のためHomebrewを使用
- **違反時の対応**: Homebrewまたはuvでの代替手段を提案

## ✅ 必須使用コマンド

### Python関連
```bash
# テスト実行
uv run python -m pytest tests/

# スクリプト実行
uv run python main.py

# パッケージ追加
uv add package-name

# 依存関係同期
uv sync
```

### 開発ツール
```bash
# リンティング
uv run ruff check .

# フォーマット
uv run ruff format .

# 型チェック
uv run mypy .
```

## 🔧 AI開発者向けチェックリスト

コマンド実行前に以下を確認：

1. **Python実行**: `uv run python` を使用しているか？
2. **依存関係**: `uv sync` または `uv add` を使用しているか？
3. **システムツール**: Homebrewまたはモダンツールを使用しているか？

## 🚨 違反検出時の自動修正

AI開発者は以下のパターンを検出した場合、自動的に修正すること：

```bash
# 検出パターン → 修正後
python3 -m pytest → uv run python -m pytest
python main.py → uv run python main.py
pip install → uv add
apt install → brew install (または代替手段提案)
```

## 📋 プロジェクト固有ルール

### MCP Docker環境
- GitHub Personal Access Token: `GITHUB_PERSONAL_ACCESS_TOKEN`
- Docker権限: 非rootユーザーでの実行
- ログ形式: 構造化JSON（UTC、ISO8601）

### 品質基準
- 全テスト: `uv run python -m pytest`
- 品質チェック: `make quality-check`
- セキュリティ: `make security`

## 🎯 成功基準

AI開発者の作業が成功とみなされる条件：

1. ✅ レガシーコマンドを一切使用していない
2. ✅ uvによる依存関係管理を正しく使用
3. ✅ モダンツールを適切に選択・提案
4. ✅ プロジェクト品質基準を満たしている

---

**重要**: このルールに違反するコマンドを実行しようとした場合、AI開発者は即座に停止し、正しいコマンドに修正してから実行すること。
