#!/usr/bin/env bats
# 検証対象: シェルスクリプト全般
# 目的: 基本的な構文と動作の確認

setup() {
    export PROJECT_ROOT="${BATS_TEST_DIRNAME}/../.."
    export SCRIPTS_DIR="${PROJECT_ROOT}/scripts"
}

@test "setup.sh: スクリプトが存在し実行可能" {
    [ -f "${SCRIPTS_DIR}/setup.sh" ]
    [ -x "${SCRIPTS_DIR}/setup.sh" ]
}

@test "setup.sh: 構文エラーがない" {
    bash -n "${SCRIPTS_DIR}/setup.sh"
}

@test "setup.sh: prepare-onlyモードが動作する" {
    run "${SCRIPTS_DIR}/setup.sh" --prepare-only
    [ "$status" -eq 0 ]
    [[ "$output" =~ "環境整備のみ完了しました" ]]
}

@test "health-check.sh: スクリプトが存在し実行可能" {
    [ -f "${SCRIPTS_DIR}/health-check.sh" ]
    [ -x "${SCRIPTS_DIR}/health-check.sh" ]
}

@test "health-check.sh: 構文エラーがない" {
    bash -n "${SCRIPTS_DIR}/health-check.sh"
}

@test "health-check.sh: --helpオプションが動作する" {
    run "${SCRIPTS_DIR}/health-check.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "使用方法" ]]
}

@test "health-check.sh: -hオプションが動作する" {
    run "${SCRIPTS_DIR}/health-check.sh" -h
    [ "$status" -eq 0 ]
    [[ "$output" =~ "使用方法" ]]
}

@test "health-check.sh: 不明なオプションでエラー終了する" {
    run "${SCRIPTS_DIR}/health-check.sh" --unknown-option
    [ "$status" -eq 1 ]
    [[ "$output" =~ "不明なオプション" ]]
}

@test "generate-ide-config.sh: スクリプトが存在し実行可能" {
    [ -f "${SCRIPTS_DIR}/generate-ide-config.sh" ]
    [ -x "${SCRIPTS_DIR}/generate-ide-config.sh" ]
}

@test "generate-ide-config.sh: 構文エラーがない" {
    bash -n "${SCRIPTS_DIR}/generate-ide-config.sh"
}

@test "generate-ide-config.sh: usage表示が動作する" {
    run "${SCRIPTS_DIR}/generate-ide-config.sh"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "使用方法" ]]
}

@test "generate-ide-config.sh: vscode設定生成が動作する" {
    run "${SCRIPTS_DIR}/generate-ide-config.sh" --ide vscode
    [ "$status" -eq 0 ]
    [[ "$output" =~ "VS Code設定を生成しました" ]]
    [ -f "${PROJECT_ROOT}/config/ide-configs/vscode/settings.json" ]
}

@test "generate-ide-config.sh: claude-desktop設定生成がGITHUB_MCP_IMAGE未設定でも動作する" {
    run env -u GITHUB_MCP_IMAGE "${SCRIPTS_DIR}/generate-ide-config.sh" --ide claude-desktop
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Claude Desktop設定を生成しました" ]]
    [ -f "${PROJECT_ROOT}/config/ide-configs/claude-desktop/claude_desktop_config.json" ]
    grep -q '"ghcr.io/github/github-mcp-server:main"' "${PROJECT_ROOT}/config/ide-configs/claude-desktop/claude_desktop_config.json"
    grep -q '"github-mcp-cache:/app/cache:rw"' "${PROJECT_ROOT}/config/ide-configs/claude-desktop/claude_desktop_config.json"
}

@test "generate-ide-config.sh: claude-desktop設定生成でdocker stdio設定が反映される" {
    run env GITHUB_MCP_IMAGE=test-image:latest "${SCRIPTS_DIR}/generate-ide-config.sh" --ide claude-desktop
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Claude Desktop設定を生成しました" ]]
    [ -f "${PROJECT_ROOT}/config/ide-configs/claude-desktop/claude_desktop_config.json" ]
    grep -q '"command": "docker"' "${PROJECT_ROOT}/config/ide-configs/claude-desktop/claude_desktop_config.json"
    grep -q '"-i"' "${PROJECT_ROOT}/config/ide-configs/claude-desktop/claude_desktop_config.json"
    grep -q '"GITHUB_PERSONAL_ACCESS_TOKEN"' "${PROJECT_ROOT}/config/ide-configs/claude-desktop/claude_desktop_config.json"
    grep -q '"test-image:latest"' "${PROJECT_ROOT}/config/ide-configs/claude-desktop/claude_desktop_config.json"
    grep -q '"stdio"' "${PROJECT_ROOT}/config/ide-configs/claude-desktop/claude_desktop_config.json"
}

@test "generate-ide-config.sh: amazonq設定生成が動作する" {
    run "${SCRIPTS_DIR}/generate-ide-config.sh" --ide amazonq
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Amazon Q設定を生成しました" ]]
    [ -f "${PROJECT_ROOT}/config/ide-configs/amazonq/mcp.json" ]
}

@test "generate-ide-config.sh: codex設定(TOML)生成が動作する" {
    run "${SCRIPTS_DIR}/generate-ide-config.sh" --ide codex
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Codex設定(TOML)を生成しました" ]]
    [ -f "${PROJECT_ROOT}/config/ide-configs/codex/config.toml" ]
}

@test "generate-ide-config.sh: copilot-cli設定(JSON)生成が動作する" {
    run "${SCRIPTS_DIR}/generate-ide-config.sh" --ide copilot-cli
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Copilot CLI設定(JSON)を生成しました" ]]
    [ -f "${PROJECT_ROOT}/config/ide-configs/copilot-cli/mcp-config.json" ]
}

@test "generate-ide-config.sh: 無効なIDE名でエラー" {
    run "${SCRIPTS_DIR}/generate-ide-config.sh" --ide invalid
    [ "$status" -eq 1 ]
    [[ "$output" =~ "未対応のIDE" ]]
}

@test "generate-ide-config.sh: --service copilot-review-mcp vscode設定生成が動作する" {
    run "${SCRIPTS_DIR}/generate-ide-config.sh" --ide vscode --service copilot-review-mcp
    [ "$status" -eq 0 ]
    [[ "$output" =~ "VS Code設定を生成しました" ]]
    [ -f "${PROJECT_ROOT}/config/ide-configs/copilot-review-mcp/vscode/settings.json" ]
}

@test "generate-ide-config.sh: --service copilot-review-mcp claude-desktop はexit 0で案内を表示する" {
    run "${SCRIPTS_DIR}/generate-ide-config.sh" --ide claude-desktop --service copilot-review-mcp
    [ "$status" -eq 0 ]
    [[ "$output" =~ "HTTP only" ]] || [[ "$output" =~ "stdio" ]]
}

@test "generate-ide-config.sh: --service mcp-gateway claude-desktop 設定生成が動作する" {
    run "${SCRIPTS_DIR}/generate-ide-config.sh" --ide claude-desktop --service mcp-gateway
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Claude Desktop設定を生成しました" ]]
    [ -f "${PROJECT_ROOT}/config/ide-configs/mcp-gateway/claude-desktop/claude_desktop_config.json" ]
    grep -q '"mcp-remote"' "${PROJECT_ROOT}/config/ide-configs/mcp-gateway/claude-desktop/claude_desktop_config.json"
    grep -q '8080' "${PROJECT_ROOT}/config/ide-configs/mcp-gateway/claude-desktop/claude_desktop_config.json"
}

@test "generate-ide-config.sh: --service mcp-gateway vscode 設定生成が動作する" {
    run "${SCRIPTS_DIR}/generate-ide-config.sh" --ide vscode --service mcp-gateway
    [ "$status" -eq 0 ]
    [[ "$output" =~ "VS Code設定を生成しました" ]]
    [ -f "${PROJECT_ROOT}/config/ide-configs/mcp-gateway/vscode/settings.json" ]
    grep -q '8080' "${PROJECT_ROOT}/config/ide-configs/mcp-gateway/vscode/settings.json"
}

@test "generate-ide-config.sh: --service mcp-gateway codex 設定生成が動作する" {
    run "${SCRIPTS_DIR}/generate-ide-config.sh" --ide codex --service mcp-gateway
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Codex設定を生成しました" ]]
    [ -f "${PROJECT_ROOT}/config/ide-configs/mcp-gateway/codex/config.toml" ]
    grep -q '8080' "${PROJECT_ROOT}/config/ide-configs/mcp-gateway/codex/config.toml"
}

@test "health-check.sh: --helpオプションにサービス説明が含まれる" {
    run "${SCRIPTS_DIR}/health-check.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "mcp-gateway" ]]
}
