# 統合テスト改善計画

## 現状分析

### 問題の概要
統合テストが以下の問題を抱えている：
1. **テスト分類が不明確**: Actions Simulator、サービス統合、E2Eが混在
2. **拡張性の欠如**: 新サービス追加時の構造が不明確
3. **E2Eテストの混在**: 統合テストにE2Eテストが含まれている

### 現在のサービス構成
稼働中のサービス（削除なし）：
- `github-mcp`: GitHub MCP Server
- `datetime-validator`: DateTime Validator
- `actions-simulator`: Actions Simulator
- `actions-server`: Actions Server
- `actions-shell`: Actions Shell

### 影響範囲
1. **Batsテスト** (`tests/integration/*.bats`)
   - `test_services.bats`: サービス起動確認
   - `test_integration.bats`: サービス統合
   - `test_actions_simulator.bats`: Actions Simulator
   - `test_security.bats`: セキュリティ

2. **Pytestテスト** (`tests/integration/*.py`)
   - Actions Simulator機能テスト
   - サービス統合テスト
   - E2Eテスト（要移動）

## 改善方針

### 基本原則
1. **明確な3層分類**: Actions Simulator / サービス統合 / E2E
2. **拡張性の確保**: 新サービス追加時の構造を明確化
3. **E2Eテストの分離**: 統合テストからE2Eテストを分離
4. **堅牢なパス解決**: `.parent`多用を排除し、プロジェクトルート取得を一元化

### アーキテクチャ方針

#### 新テスト構造（3層分類）
```
tests/
├── unit/                          # 単体テスト
├── integration/                   # 統合テスト（再編成）
│   ├── actions/                   # Actions Simulator統合テスト
│   │   ├── test_actions_service.py
│   │   ├── test_simulation_service.py
│   │   ├── test_simulation_service_integration.py
│   │   ├── test_enhanced_act_wrapper.py
│   │   ├── test_act_wrapper_with_tracer.py
│   │   ├── test_diagnostic_service.py
│   │   ├── test_performance_monitor.py
│   │   ├── test_performance_monitor_enhanced.py
│   │   ├── test_auto_recovery.py
│   │   └── test_actions_simulator.bats
│   ├── services/                  # サービス統合テスト
│   │   ├── test_github_mcp.py
│   │   ├── test_datetime_validator.py
│   │   ├── test_services.bats
│   │   └── test_integration.bats
│   ├── common/                    # 共通テスト
│   │   ├── test_documentation_consistency.py
│   │   ├── test_template_validation.py
│   │   ├── test_platform_support.py
│   │   └── test_security.bats
│   └── shared/                    # 共通ユーティリティ
│       └── test_helpers.sh
└── e2e/                           # E2Eテスト
    ├── test_integration_final.py          # ← 移動
    ├── test_docker_integration_complete.py # ← 移動
    ├── test_docker_integration_checker.py  # ← 移動
    ├── test_hangup_integration.py         # ← 移動
    ├── test_support_integration.py        # ← 移動
    └── (既存のE2Eテスト)
```

## 実装計画

### Phase 1: テスト分類と整理（優先度: 高）

#### 1.1 テストファイルの分類

**Actions Simulator統合テスト** → `tests/integration/actions/`
- test_actions_service.py
- test_simulation_service.py
- test_simulation_service_integration.py
- test_enhanced_act_wrapper.py
- test_act_wrapper_with_tracer.py
- test_diagnostic_service.py
- test_performance_monitor.py
- test_performance_monitor_enhanced.py
- test_auto_recovery.py
- test_actions_simulator.bats

**サービス統合テスト** → `tests/integration/services/`
- test_services.bats（既存）
- test_integration.bats（既存）
- 将来: test_github_mcp_integration.py
- 将来: test_datetime_validator_integration.py

**共通テスト** → `tests/integration/common/`
- test_documentation_consistency.py
- test_template_validation.py
- test_platform_support.py
- test_security.bats

**E2Eテスト** → `tests/e2e/`（移動）
- test_integration_final.py
- test_docker_integration_complete.py
- test_docker_integration_checker.py
- test_hangup_integration.py
- test_support_integration.py

#### 1.2 実装手順
1. ディレクトリ作成: `actions/`, `services/`, `common/`
2. Actions Simulator関連テストを `actions/` に移動
3. サービステストを `services/` に移動
4. 共通テストを `common/` に移動
5. E2Eテストを `tests/e2e/` に移動
6. 共通ヘルパーを `shared/` に整理

### Phase 2: CIワークフロー修正（優先度: 高）

#### 2.1 `pytest` ジョブの修正

**現状の問題**:
- `continue-on-error: true` で失敗しても成功扱いになる

**修正案**:
```yaml
pytest:
  steps:
    - name: Run pytest (unit tests)
      id: unit-tests
      run: uv run pytest tests/unit/ -v --tb=short --maxfail=5
      continue-on-error: false

    - name: Run pytest (integration tests - actions)
      id: integration-actions
      run: uv run pytest tests/integration/actions/ -v --tb=short
      continue-on-error: false

    - name: Run pytest (integration tests - services)
      id: integration-services
      run: uv run pytest tests/integration/services/ -v --tb=short
      continue-on-error: false

    - name: Run pytest (integration tests - common)
      id: integration-common
      run: uv run pytest tests/integration/common/ -v --tb=short
      continue-on-error: false

    - name: Run pytest (e2e tests - selected)
      id: e2e-tests
      run: uv run pytest tests/e2e/test_comprehensive_integration.py -v --tb=short
      continue-on-error: false

    - name: Check test results
      if: always()
      run: |
        echo "## テスト結果サマリ" >> $GITHUB_STEP_SUMMARY
        echo "" >> $GITHUB_STEP_SUMMARY
        echo "- Unit Tests: ${{ steps.unit-tests.outcome }}" >> $GITHUB_STEP_SUMMARY
        echo "- Integration (Actions): ${{ steps.integration-actions.outcome }}" >> $GITHUB_STEP_SUMMARY
        echo "- Integration (Services): ${{ steps.integration-services.outcome }}" >> $GITHUB_STEP_SUMMARY
        echo "- Integration (Common): ${{ steps.integration-common.outcome }}" >> $GITHUB_STEP_SUMMARY
        echo "- E2E Tests: ${{ steps.e2e-tests.outcome }}" >> $GITHUB_STEP_SUMMARY

        # 統合テストが失敗した場合はジョブを失敗させる
        if [[ "${{ steps.integration-actions.outcome }}" == "failure" ]] || \
           [[ "${{ steps.integration-services.outcome }}" == "failure" ]] || \
           [[ "${{ steps.integration-common.outcome }}" == "failure" ]]; then
          echo "❌ 統合テストが失敗しました"
          exit 1
        fi
```

#### 2.2 `bats-test` ジョブの修正

**修正案**:
```yaml
bats-test:
  steps:
    - name: Run Bats tests (actions)
      run: bats tests/integration/actions/*.bats

    - name: Run Bats tests (services)
      run: bats tests/integration/services/*.bats

    - name: Run Bats tests (common)
      run: bats tests/integration/common/*.bats
```

#### 2.3 `integration` ジョブの修正

**現状の問題**:
- `|| echo` でエラーを隠蔽している

**修正案**:
```yaml
integration:
  steps:
    - name: Build and start services
      run: |
        docker compose build
        docker compose up -d github-mcp datetime-validator actions-simulator

    - name: Run integration tests
      id: integration-tests
      run: |
        uv run pytest tests/integration/ -v --tb=short
      continue-on-error: false

    - name: Check integration test results
      if: always()
      run: |
        if [[ "${{ steps.integration-tests.outcome }}" == "failure" ]]; then
          echo "❌ 統合テストが失敗しました"
          echo "ログを確認して問題を修正してください"
          exit 1
        fi
```

### Phase 3: テストコード修正（優先度: 中）

#### 3.1 プロジェクトルート取得の一元化（重要）

**問題**: `.parent`の多用によりテストフォルダ再編に脆弱

**解決策**: 共通ユーティリティでプロジェクトルートを一元管理

**実装**: `tests/conftest.py`（pytest共通設定）
```python
"""pytest共通設定 - プロジェクトルート取得を一元化"""
import sys
from pathlib import Path

# プロジェクトルートの検出（pyproject.tomlの存在で判定）
def find_project_root(start_path: Path | None = None) -> Path:
    """プロジェクトルートを検出

    pyproject.toml, .git, setup.pyのいずれかが存在するディレクトリを
    プロジェクトルートとして返す。

    Args:
        start_path: 検索開始パス（デフォルト: このファイルの場所）

    Returns:
        プロジェクトルートのPath

    Raises:
        RuntimeError: プロジェクトルートが見つからない場合
    """
    if start_path is None:
        start_path = Path(__file__).resolve().parent

    current = start_path
    for _ in range(10):  # 最大10階層まで遡る
        markers = [
            current / "pyproject.toml",
            current / ".git",
            current / "setup.py",
        ]
        if any(marker.exists() for marker in markers):
            return current

        if current.parent == current:  # ルートディレクトリに到達
            break
        current = current.parent

    raise RuntimeError(
        f"プロジェクトルートが見つかりません（開始: {start_path}）"
    )

# グローバル変数として公開
PROJECT_ROOT = find_project_root()

# Pythonパスに追加（絶対インポートを可能にする）
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
```

**使用例**:
```python
# テストファイル内での使用
from conftest import PROJECT_ROOT

def test_something():
    config_file = PROJECT_ROOT / "pyproject.toml"
    assert config_file.exists()

    # .parentを使わずに直接アクセス
    workflows_dir = PROJECT_ROOT / ".github" / "workflows"
```

#### 3.2 移動後のインポートパス修正

**対象**: 移動したすべてのテストファイル

**修正内容**:
```python
# ❌ 脆弱: 相対パスの多用
project_root = Path(__file__).parent.parent.parent.parent

# ✅ 堅牢: conftest経由
from conftest import PROJECT_ROOT
project_root = PROJECT_ROOT

# 共通ユーティリティのインポート
from tests.integration.shared import test_helpers
```

#### 3.3 Batsテストのヘルパーパス修正

**対象**: すべての.batsファイル

**修正内容**:
```bash
# ❌ 脆弱: 相対パス
load test_helper

# ✅ 堅牢: プロジェクトルートからの絶対パス
# tests/integration/shared/test_helpers.shで環境変数を設定
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && git rev-parse --show-toplevel)"
load "${PROJECT_ROOT}/tests/integration/shared/test_helpers.sh"
```

**共通ヘルパー** (`tests/integration/shared/test_helpers.sh`):
```bash
#!/usr/bin/env bash
# プロジェクトルート取得の共通関数

get_project_root() {
    # gitリポジトリルートを取得（最も信頼性が高い）
    if command -v git >/dev/null 2>&1; then
        git rev-parse --show-toplevel 2>/dev/null && return
    fi

    # フォールバック: pyproject.tomlを探す
    local current="$PWD"
    for _ in {1..10}; do
        if [[ -f "${current}/pyproject.toml" ]]; then
            echo "${current}"
            return
        fi
        [[ "${current}" == "/" ]] && break
        current="$(dirname "${current}")"
    done

    echo "Error: Project root not found" >&2
    return 1
}

# グローバル変数として公開
export PROJECT_ROOT="$(get_project_root)"
```

### Phase 4: ドキュメント更新（優先度: 中）

#### 4.1 更新対象
- `docs/actions/TESTING.md`: 新しいテスト構造を説明
- `.github/workflows/ci.yml`: コメント更新
- `tests/README.md`: テスト構造ガイド作成

#### 4.2 テスト構造ガイド
```markdown
# テスト構造ガイド

## 統合テスト分類

### Actions Simulator統合テスト (`tests/integration/actions/`)
Actions Simulatorの機能テスト

### サービス統合テスト (`tests/integration/services/`)
複数サービス間の連携テスト

### 共通テスト (`tests/integration/common/`)
ドキュメント、テンプレート、プラットフォーム対応

### E2Eテスト (`tests/e2e/`)
エンドツーエンドの完全なシナリオテスト
```

## 実装優先順位

### 🔴 Critical（即座に実施）
1. **Phase 1**: テストファイルの分類と移動（3層構造）
2. **Phase 2**: CIワークフロー修正（pytest/bats/integration）
3. **Phase 3.1**: プロジェクトルート取得の一元化（`conftest.py`作成）
4. **Phase 3.2-3.3**: インポートパス・ヘルパーパス修正

### 🟢 Medium（余裕があれば実施）
4. **Phase 4**: ドキュメント更新

## 成功基準

### Phase 1完了時 ✅
- [x] テストファイルが適切に分類・移動されている
- [x] 既存のテストが実行可能（スキップ含む）

### Phase 2完了時 ✅
- [x] CIワークフローが3層構造に対応
- [x] `docker-services-integration` ジョブに改名・明確化
- [x] エラー隠蔽を排除、結果判定を追加

### Phase 3完了時
- [ ] `conftest.py`でプロジェクトルート取得が一元化されている
- [ ] `.parent`の多用が排除されている
- [ ] インポートパスが正しく修正されている
- [ ] Batsテストのヘルパーパスが正しい
- [ ] すべてのテストが実行可能
- [ ] テストフォルダ再編に対して堅牢な構造になっている

### Phase 4完了時
- [ ] ドキュメントが最新の構造を反映している
- [ ] アーカイブの説明が明確である

## リスクと対策

### リスク1: テスト移動時の破損
**対策**:
- Git履歴を保持するため `git mv` を使用
- 移動後に即座にテスト実行して確認

### リスク2: CI失敗の長期化
**対策**:
- Phase 1とPhase 2を同一PRで実施
- ドラフトPRで事前検証

### リスク3: インポートパスの破損
**対策**:
- 移動後に即座にテスト実行
- 相対インポートを適切に修正

## 次のアクション

1. ✅ **Phase 1完了**: テストファイルの3層分類と移動
2. ✅ **Phase 2完了**: CIワークフロー修正と明確化
3. ⏳ **Phase 3実施中**: テストコード修正（インポートパス・ヘルパーパス）
4. 📋 **Phase 4予定**: ドキュメント更新

### 現在の優先タスク

**Phase 3: テストコード修正**
- conftest.py作成済み ✅
- test_helpers.sh作成済み ✅
- 次: 移動したテストファイルのインポートパス修正（必要に応じて）

---

**作成日**: 2025-01-24
**最終更新**: 2025-01-24
**ステータス**: ✅ Phase 1-2完了、Phase 3-4実施中
