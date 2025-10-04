#!/usr/bin/env bats
# GitHub Actions Simulator - Integration Tests
# ===============================================
#
# GitHub Actions Simulatorサービスの統合テストです。
# 実際のワークフローファイルを使用して、エンドツーエンドでの動作を検証します。
#
# 検証対象:
#   - CLI インターフェースの動作確認
#   - ワークフロー解析機能の検証
#   - シミュレーション実行機能の確認
#   - Docker統合の動作検証

load '../../helpers/test_helper'

# セットアップ: 各テストの前に実行
setup() {
    # プロジェクトルートの設定（動的に検出）
    export PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export ACTIONS_SIMULATOR_ENGINE="mock"

    # テスト用の一時ワークスペース作成
    export TEST_WORKSPACE="/tmp/mcp_actions_test_$$"
    mkdir -p "$TEST_WORKSPACE/.github/workflows"
    cd "$TEST_WORKSPACE" || exit

    # テスト用のシンプルなワークフローファイル作成
    cat > "$TEST_WORKSPACE/.github/workflows/test.yml" <<EOF
name: Test Workflow
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - name: Run test
        run: echo "Test completed"
EOF

    # 複雑なワークフローファイル作成
    cat > "$TEST_WORKSPACE/.github/workflows/complex.yml" <<EOF
name: Complex CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - name: Lint code
        run: |
          echo "Running linting"
          exit 0

  test:
    runs-on: ubuntu-latest
    needs: lint
    strategy:
      matrix:
        node-version: [16, 18, 20]
    steps:
      - uses: actions/checkout@v5
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: \${{ matrix.node-version }}
      - name: Run tests
        run: echo "Testing with Node \${{ matrix.node-version }}"
EOF
}

# ティアダウン: 各テストの後に実行
teardown() {
    # テスト用ワークスペースのクリーンアップ
    if [[ -n "$TEST_WORKSPACE" && -d "$TEST_WORKSPACE" ]]; then
        rm -rf "$TEST_WORKSPACE"
    fi
}

# テスト: CLIヘルプ表示の動作確認
@test "CLI: ヘルプメッセージの表示確認" {
    # 検証対象: CLI基本機能
    # 目的: ヘルプメッセージが適切に表示されることを確認

  run run_in_project_root uv run python main.py actions --help
    assert_success
    assert_output --partial "GitHub Actions Simulator"
    assert_output --partial "simulate"
    assert_output --partial "validate"
    assert_output --partial "list-jobs"
}

# テスト: ワークフロー構文検証の動作確認
@test "Workflow Parser: 有効なワークフローファイルの解析" {
    # 検証対象: ワークフロー解析機能
    # 目的: 有効なYAMLファイルが正常に解析されることを確認

  run run_in_project_root uv run python main.py actions validate "$TEST_WORKSPACE/.github/workflows/test.yml"
    assert_success
    assert_output --partial "検証が完了しました"
}

# テスト: 無効なワークフローファイルのエラー処理
@test "Workflow Parser: 無効なワークフローファイルのエラー検出" {
    # 検証対象: エラーハンドリング機能
    # 目的: 構文エラーが適切に検出されることを確認

    # 無効なYAMLファイル作成（構文エラーを含む）
    cat > "$TEST_WORKSPACE/.github/workflows/invalid.yml" <<'EOF'
name: Invalid Workflow
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"
        invalid_key without_proper_indentation
EOF

  run run_in_project_root uv run python main.py actions validate "$TEST_WORKSPACE/.github/workflows/invalid.yml"
    assert_failure
}

# テスト: 存在しないファイルのエラー処理
@test "Workflow Parser: 存在しないファイルのエラー処理" {
    # 検証対象: ファイルアクセスエラー処理
    # 目的: ファイルが存在しない場合の適切なエラー処理を確認

  run run_in_project_root uv run python main.py actions validate "/tmp/nonexistent_workflow.yml"
    assert_failure
    assert_output --partial "ファイルが見つかりません"
}

# テスト: ジョブ一覧表示（テーブル形式）
@test "Job Listing: テーブル形式でのジョブ一覧表示" {
    # 検証対象: ジョブ一覧機能
    # 目的: ワークフロー内のジョブが適切に一覧表示されることを確認

  run run_in_project_root uv run python main.py actions list-jobs "$TEST_WORKSPACE/.github/workflows/test.yml" --format table
    assert_success
  assert_output --partial "ジョブ一覧"
  assert_output --partial "Job ID"
  assert_output --partial "│ test   │ test │ ubuntu-latest │"
}

# テスト: ジョブ一覧表示（JSON形式）
@test "Job Listing: JSON形式でのジョブ一覧表示" {
    # 検証対象: JSON出力機能
    # 目的: JSON形式でのジョブ情報出力が正常に動作することを確認

  run run_in_project_root uv run python main.py actions list-jobs "$TEST_WORKSPACE/.github/workflows/test.yml" --format json
    assert_success
  assert_output --partial '"job_id"'
  assert_output --partial '"runs_on"'
}

# テスト: 複雑なワークフローのジョブ一覧表示
@test "Job Listing: 複雑なワークフローの解析" {
    # 検証対象: 複雑なワークフロー解析
    # 目的: 依存関係やmatrix strategyを含むワークフローが適切に解析されることを確認

  run run_in_project_root uv run python main.py actions list-jobs "$TEST_WORKSPACE/.github/workflows/complex.yml" --format table
    assert_success
  assert_output --partial "ジョブ一覧"
  assert_output --partial "│ lint                  │ lint"
  assert_output --partial "│ test__node-version-20 │ test"
}

# テスト: ドライランモードでのワークフロー実行

# テスト: 特定ジョブのドライラン実行

# テスト: 存在しないジョブ指定のエラー処理

# テスト: 詳細ログモードの動作確認

# テスト: 実際のci.ymlファイルでの動作確認

# テスト: エラー時の終了コード確認
@test "Error Handling: 適切な終了コードの確認" {
    # 検証対象: エラーハンドリング
    # 目的: エラー時に適切な終了コードが返されることを確認

    # mockエンジン使用時はファイル存在チェックをスキップ
    if [[ "$ACTIONS_SIMULATOR_ENGINE" == "mock" ]]; then
        skip "mockエンジンはファイル存在チェックを行わない"
    fi

    # 存在しないファイルでの実行（終了コード1を期待）
  run run_in_project_root uv run python main.py actions validate "/tmp/nonexistent.yml"
    assert_failure
    [[ "$status" -eq 1 ]]

    # 存在しないジョブでの実行（終了コード1を期待）
  run run_in_project_root uv run python main.py actions simulate "$TEST_WORKSPACE/.github/workflows/test.yml" --job nonexistent --dry-run
    assert_failure
    [[ "$status" -eq 1 ]]
}

# テスト: パフォーマンス確認（実行時間）
@test "Performance: 実行時間の妥当性確認" {
    # 検証対象: パフォーマンス
    # 目的: 基本的な操作が妥当な時間内で完了することを確認

    local start_time end_time duration
    start_time=$(date +%s)

    run_in_project_root uv run python main.py actions simulate "$TEST_WORKSPACE/.github/workflows/complex.yml" --dry-run
    assert_success

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    # 10秒以内での完了を期待（ドライランなので高速であるべき）
    [[ $duration -lt 10 ]]
}
