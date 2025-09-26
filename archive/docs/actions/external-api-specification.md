# GitHub Actions Simulator - 外部API仕様書

## 概要

このドキュメントは、MCP Docker Actions Simulatorを他プロジェクト・CI/CD・ローカルツールから呼び出すためのAPI設計をまとめたものです。

---

## 1. REST API

### サーバーモード起動
```bash
python main.py actions serve --port 9000
```

### エンドポイント
- `POST /simulate`
  - パラメータ:
    - `workflow_path`: ワークフローファイルの絶対パス
    - `event`: 実行イベント（例: push, pull_request）
    - `job`: 実行ジョブ名（省略可）
  - レスポンス:
    ```json
    {
      "status": "success",
      "result": { ... },
      "codeql": { ... }
    }
    ```

### 認証
- APIキーまたはJWTトークン（環境変数/ヘッダー）

---

## 2. CLI API

### コマンド実行例
```bash
mcp-docker-actions simulate /path/to/ci.yml --event pull_request --job lint
```

- 標準出力で結果返却
- サブプロセス呼び出し可能

---

## 3. Docker API

### コンテナ実行例
```bash
docker run --rm -v $PWD/.github:/workflows mcp-docker-actions \
  simulate /workflows/ci.yml --event push
```

- ボリュームでワークフローを渡す
- 結果は標準出力またはファイル出力

---

## 4. Python API

### ライブラリ呼び出し例
```python
from mcp_docker_actions import simulate_workflow
result = simulate_workflow(workflow_path="...", event="push")
```

- 関数型API
- 戻り値はdict形式

---

## 5. セキュリティ・権限
- REST APIは認証必須
- Docker/CLIは実行ユーザー権限・ボリューム制限
- Python APIはローカル利用推奨

---

## 6. 使用例

### 他プロジェクトからの呼び出し
```bash
curl -X POST http://localhost:9000/simulate \
  -H "Authorization: Bearer <token>" \
  -d '{"workflow_path": "/workflows/ci.yml", "event": "push"}'
```

### CI/CD統合
```yaml
jobs:
  local-actions-simulate:
    runs-on: ubuntu-latest
    steps:
      - name: Run local simulator
        run: |
          docker run --rm -v ${{ github.workspace }}/.github:/workflows mcp-docker-actions simulate /workflows/ci.yml --event push
```

---

## 7. FAQ
- Q: APIサーバーは複数同時実行可能？
  - A: ポート指定で複数起動可能
- Q: ワークフローのYAMLバリデーションは？
  - A: API/CLIともに自動検証
- Q: CodeQL統合は？
  - A: `codeql`パラメータで制御可能

---

## 8. 更新履歴
- **2025-09-25**: 初版作成
