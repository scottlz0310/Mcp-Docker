#!/usr/bin/env python3
"""Act log analyzer - 失敗原因を特定"""

import re
from pathlib import Path
from typing import Dict


def analyze_log(log_file: Path) -> Dict:
    """ログを解析して失敗原因を特定"""
    if not log_file.exists():
        return {"error": "ログファイルが見つかりません"}

    content = log_file.read_text()

    # エラーパターン
    errors = []
    warnings = []

    # ❌ Failure パターン
    for match in re.finditer(r"❌\s+Failure - Main (.+?) \[", content):
        errors.append(f"失敗したステップ: {match.group(1)}")

    # ::error パターン
    for match in re.finditer(r"::error[^:]*::(.+)", content):
        errors.append(f"エラー: {match.group(1)}")

    # exitcode パターン
    for match in re.finditer(r"exitcode '(\d+)': (.+)", content):
        errors.append(f"終了コード {match.group(1)}: {match.group(2)}")

    # Error: パターン
    for match in re.finditer(r"^Error: (.+)$", content, re.MULTILINE):
        errors.append(f"エラー: {match.group(1)}")

    # 警告
    for match in re.finditer(r"⚠️\s+(.+)", content):
        warnings.append(match.group(1))

    # 実行時間
    duration_match = re.search(r"実行時間: ([\d.]+)秒", content)
    duration = duration_match.group(1) if duration_match else None

    # 終了コード
    exit_code_match = re.search(r"終了コード: (\d+)", content)
    exit_code = int(exit_code_match.group(1)) if exit_code_match else None

    return {
        "errors": errors,
        "warnings": warnings,
        "duration": duration,
        "exit_code": exit_code,
        "success": exit_code == 0 if exit_code is not None else None,
    }


def print_analysis(analysis: Dict):
    """解析結果を表示"""
    if "error" in analysis:
        print(f"❌ {analysis['error']}")
        return

    print("📊 ログ解析結果")
    print("=" * 50)

    if analysis["success"]:
        print("✅ ステータス: 成功")
    else:
        print("❌ ステータス: 失敗")

    if analysis["duration"]:
        print(f"⏱️  実行時間: {analysis['duration']}秒")

    if analysis["exit_code"] is not None:
        print(f"🔢 終了コード: {analysis['exit_code']}")

    print()

    if analysis["errors"]:
        print("🔴 エラー:")
        for i, error in enumerate(analysis["errors"], 1):
            print(f"  {i}. {error}")
        print()

    if analysis["warnings"]:
        print("⚠️  警告:")
        for i, warning in enumerate(analysis["warnings"], 1):
            print(f"  {i}. {warning}")
        print()

    # 解決策の提案
    if analysis["errors"]:
        print("💡 解決策:")
        for error in analysis["errors"]:
            if "Ruff" in error or "コード品質" in error:
                print("  • コードフォーマット: uv run ruff format .")
                print("  • コード修正: uv run ruff check --fix .")
                break
            elif "pytest" in error or "テスト" in error:
                print("  • テスト実行: uv run pytest -v")
                break


if __name__ == "__main__":
    import sys

    log_file = Path("logs/actions.log")
    if len(sys.argv) > 1:
        log_file = Path(sys.argv[1])

    analysis = analyze_log(log_file)
    print_analysis(analysis)
