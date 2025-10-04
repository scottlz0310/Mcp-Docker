# テストヘルパー（Test Helpers）

## 目的

このディレクトリには、**テスト間で共有される共通ヘルパー関数・ユーティリティ**を配置します。

## 対象

- モック・フィクスチャの生成ヘルパー
- テストデータの準備ヘルパー
- アサーション拡張
- Docker操作の共通関数
- ログ・デバッグユーティリティ

## ファイル例

- `docker_helpers.py` - Docker操作の共通関数
- `fixtures_factory.py` - テストデータ生成
- `mock_helpers.py` - モックオブジェクト生成
- `assertions.py` - カスタムアサーション
- `test_helper.bash` - Batsテスト用ヘルパー（シェルスクリプト）

## 使用例

```python
# tests/helpers/docker_helpers.py
def start_test_container(image_name: str, port: int = 8080):
    """テスト用Dockerコンテナを起動"""
    # ...
    return container

def cleanup_test_containers(prefix: str = "test_"):
    """テストコンテナをクリーンアップ"""
    # ...

# tests/unit/test_something.py
from tests.helpers.docker_helpers import start_test_container

def test_with_container():
    container = start_test_container("test-image")
    # テスト実行
    # ...
```

## ベストプラクティス

1. **再利用性**: 複数のテストで使う処理をヘルパー化
2. **明確な命名**: 何をするヘルパーか一目でわかる名前
3. **適切なエラーハンドリング**: ヘルパー内でエラーを適切に処理
4. **ドキュメント**: docstringで用途・引数・戻り値を明記
5. **テスト**: ヘルパー自体もテスト可能にする
