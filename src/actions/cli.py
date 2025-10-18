#!/usr/bin/env python3
"""GitHub Actions ワークフローをローカルで実行"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime


def main() -> None:
    """GitHub Actionsワークフローをローカルで実行"""
    # actのインストール確認
    try:
        subprocess.run(["act", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 'act'がインストールされていません")
        print("📦 インストール: brew install act")
        sys.exit(1)

    # 引数取得
    if os.environ.get("_MCP_DOCKER_ARGS"):
        import json

        args = json.loads(os.environ["_MCP_DOCKER_ARGS"])
    else:
        args = sys.argv[1:]

    # シンプルな使い方: mcp-docker actions <workflow>
    workflow = None
    if args and not args[0].startswith("-"):
        workflow = args[0]
        args = ["-W"] + args
    elif args and args[0] == "simulate":
        workflow = args[1] if len(args) > 1 else None
        args = ["-W"] + args[1:]

    # ログ設定
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "actions.log"

    # 実行開始
    start_time = datetime.utcnow()
    with open(log_file, "a") as f:
        f.write(f"\n{'=' * 50}\n")
        f.write(f"実行開始: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"ワークフロー: {workflow or '未指定'}\n")
        f.write(f"{'=' * 50}\n\n")

    # act実行
    cmd = ["act"] + args
    if workflow:
        print(f"🚀 {workflow} を実行中...")
    else:
        print(f"🚀 実行中: {' '.join(cmd)}")
    print()

    try:
        with open(log_file, "a") as f:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            # 出力
            output = result.stdout
            print(output, end="")
            f.write(output)

            # 終了処理
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            summary = f"\n{'=' * 50}\n"
            summary += f"終了: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            summary += f"結果: {'成功' if result.returncode == 0 else '失敗'}\n"
            summary += f"実行時間: {duration:.1f}秒\n"
            summary += f"{'=' * 50}\n"
            f.write(summary)

            print()
            if result.returncode == 0:
                print(f"✅ 成功 ({duration:.1f}秒)")
            else:
                print(f"❌ 失敗 (終了コード: {result.returncode})")
                print()

                # 失敗時は自動解析
                try:
                    from .log_analyzer import analyze_log, print_analysis

                    print("🔍 失敗原因を解析中...")
                    print()
                    analysis = analyze_log(log_file)
                    print_analysis(analysis)
                except Exception:
                    pass

            print(f"\n📝 ログ: {log_file}")
            sys.exit(result.returncode)

    except KeyboardInterrupt:
        print("\n⏹️  中断されました")
        sys.exit(130)
    except Exception as e:
        print(f"❌ エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
