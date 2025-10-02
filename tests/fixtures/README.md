# テストフィクスチャ（Test Fixtures）

## 目的

このディレクトリには、**テストで使用するサンプルデータ・設定ファイル・モックデータ**を配置します。

## 対象

- サンプルワークフローファイル（YAML）
- テスト用設定ファイル（JSON, TOML, etc.）
- モックAPIレスポンス（JSON）
- テストデータ（CSV, テキストファイル等）
- テスト用Docker Compose設定

## ディレクトリ構造例

```text
fixtures/
├── workflows/              # サンプルワークフローファイル
│   ├── simple_workflow.yml
│   ├── complex_workflow.yml
│   └── invalid_workflow.yml
├── configs/               # テスト用設定ファイル
│   ├── test_config.json
│   └── test_env.toml
├── responses/             # モックAPIレスポンス
│   ├── github_api_success.json
│   └── github_api_error.json
└── docker/                # テスト用Docker設定
    └── docker-compose.test.yml
```

## 使用例

```python
# tests/unit/test_workflow_parser.py
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

def test_parse_simple_workflow():
    workflow_file = FIXTURES_DIR / "workflows" / "simple_workflow.yml"
    result = parse_workflow(workflow_file)
    assert result.is_valid()

@pytest.fixture
def mock_github_response():
    """GitHub API レスポンスのモック"""
    response_file = FIXTURES_DIR / "responses" / "github_api_success.json"
    with open(response_file) as f:
        return json.load(f)
```

## ベストプラクティス

1. **バージョン管理**: フィクスチャファイルはGitにコミット
2. **最小限のデータ**: 必要最小限のデータに絞る
3. **説明的な命名**: ファイル名で内容がわかるように
4. **README追加**: 各サブディレクトリにREADMEで用途を説明
5. **更新管理**: 古いフィクスチャは定期的に見直し・削除

## 注意事項

- **機密情報を含めない**: APIキー、パスワード等は絶対に含めない
- **サイズに注意**: 大きすぎるファイルはリポジトリに含めない
- **自動生成**: 可能な限りテスト内で動的に生成することも検討
