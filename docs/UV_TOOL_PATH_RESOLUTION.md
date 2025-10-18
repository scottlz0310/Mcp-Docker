# uv tool install パス解決戦略

## 問題

uv tool installでは以下の2つの異なるパス解決要件がある:

1. **Dockerイメージ**: グローバルキャッシュ（絶対パス）
2. **ワークフローファイル**: ユーザーのプロジェクト（相対パス）

## 解決策

### 1. 二重ルート戦略

```bash
# PACKAGE_ROOT: インストールされたパッケージの場所（Docker関連ファイル用）
PACKAGE_ROOT="${SCRIPT_DIR}/.."

# PROJECT_ROOT: ユーザーのカレントディレクトリ（ワークフロー用）
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
```

### 2. パス解決ルール

#### Dockerイメージ（絶対パス）
```bash
# docker-compose.ymlはPACKAGE_ROOTから解決
compose_file="${PACKAGE_ROOT}/docker-compose.yml"

# Docker Composeコマンドで明示的に指定
docker compose -f "$compose_file" ...
```

#### ワークフローファイル（相対パス）
```bash
# ワークフローはPROJECT_ROOT相対
WORKFLOW=".github/workflows/ci.yml"

# ボリュームマウントでPROJECT_ROOTをマップ
-v "${PROJECT_ROOT}/.github:/app/.github:ro"
```

### 3. 環境変数による制御

```bash
# main.pyから設定
export PROJECT_ROOT="$(pwd)"
export PROJECT_ROOT_FROM_ENV="1"

# run-actions.shで検出
if [[ -n "${PROJECT_ROOT_FROM_ENV:-}" ]]; then
  # uv tool installモード
  PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
  PACKAGE_ROOT="${SCRIPT_DIR}/.."
else
  # 開発モード
  PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
  PACKAGE_ROOT="${PROJECT_ROOT}"
fi
```

## 実装詳細

### main.py
```python
if service == "actions":
    env = os.environ.copy()
    env['PROJECT_ROOT'] = os.getcwd()  # ユーザーのcwd
    env['PROJECT_ROOT_FROM_ENV'] = '1'
    result = subprocess.run(cmd, check=False, env=env, cwd=os.getcwd())
```

### run-actions.sh
```bash
# パス解決
PACKAGE_ROOT="${SCRIPT_DIR}/.."
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

# Docker Compose実行
compose_file="${PACKAGE_ROOT}/docker-compose.yml"
docker compose -f "$compose_file" \
  -v "${PROJECT_ROOT}/.github:/app/.github:ro" \
  ...
```

### pyproject.toml
```toml
[tool.hatch.build.targets.wheel.force-include]
"docker-compose.yml" = "docker-compose.yml"
"Dockerfile" = "Dockerfile"
".actrc" = ".actrc"
".env.ci" = ".env.ci"
```

## 使用例

### 開発時
```bash
cd /path/to/mcp-docker
./scripts/run-actions.sh .github/workflows/ci.yml
# PROJECT_ROOT=/path/to/mcp-docker
# PACKAGE_ROOT=/path/to/mcp-docker
```

### uv tool install後
```bash
cd /path/to/user-project
mcp-docker actions .github/workflows/ci.yml
# PROJECT_ROOT=/path/to/user-project (ユーザーのcwd)
# PACKAGE_ROOT=~/.local/share/uv/tools/mcp-docker (インストール先)
```

## 利点

1. **Dockerイメージの再利用**: グローバルキャッシュで効率的
2. **ワークフローの柔軟性**: 任意のプロジェクトで実行可能
3. **透過的な動作**: ユーザーは意識する必要なし
4. **開発体験の維持**: 既存の開発フローに影響なし

## テスト

```bash
# 開発モードテスト
cd /path/to/mcp-docker
./scripts/run-actions.sh --check-deps

# uv tool installテスト
uv tool install .
cd /tmp/test-project
mkdir -p .github/workflows
echo "name: test" > .github/workflows/test.yml
mcp-docker actions .github/workflows/test.yml
```
