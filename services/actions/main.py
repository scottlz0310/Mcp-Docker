#!/usr/bin/env python3
"""
GitHub Actions Simulator - Main Entry Point
===========================================

GitHub Actions ワークフローのシミュレーション実行を行うメインモジュールです。

機能:
    - simulate: ワークフローを実行する
    - validate: ワークフローの構文をチェックする
    - list-jobs: ワークフロー内のジョブ一覧を表示する

"""

import sys
import argparse
import json
from pathlib import Path

# 内部モジュール
from .workflow_parser import WorkflowParser
from .simulator import WorkflowSimulator
from .logger import ActionsLogger


def main():
    """
    GitHub Actions Simulator のメインエントリーポイント
    """
    parser = argparse.ArgumentParser(
        description="GitHub Actions Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py actions simulate .github/workflows/ci.yml
  python main.py actions validate .github/workflows/deploy.yml
  python main.py actions list-jobs .github/workflows/ci.yml --format json
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='利用可能なコマンド')

    # simulate コマンド
    simulate_parser = subparsers.add_parser('simulate', help='ワークフローを実行')
    simulate_parser.add_argument('workflow_file', help='ワークフローYAMLファイルのパス')
    simulate_parser.add_argument('--job', '-j', help='実行する特定のジョブ名')
    simulate_parser.add_argument('--env-file', help='環境変数ファイル(.env)')
    simulate_parser.add_argument('--dry-run', action='store_true',
                                help='実際に実行せずにプランを表示')
    simulate_parser.add_argument('--verbose', '-v', action='store_true',
                                help='詳細ログを表示')
    simulate_parser.add_argument('--engine', choices=['builtin', 'act'],
                                default='builtin', help='シミュレーションエンジン')

    # validate コマンド
    validate_parser = subparsers.add_parser('validate', help='ワークフローの構文をチェック')
    validate_parser.add_argument('workflow_file', help='ワークフローYAMLファイルのパス')
    validate_parser.add_argument('--strict', action='store_true', help='厳密な検証を実行')

    # list-jobs コマンド
    list_parser = subparsers.add_parser('list-jobs', help='ジョブ一覧を表示')
    list_parser.add_argument('workflow_file', help='ワークフローYAMLファイルのパス')
    list_parser.add_argument('--format', choices=['table', 'json'], default='table', help='出力形式')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # ロガー設定
    logger = ActionsLogger(verbose=getattr(args, 'verbose', False))

    try:
        if args.command == 'simulate':
            return run_simulate(args, logger)
        elif args.command == 'validate':
            return run_validate(args, logger)
        elif args.command == 'list-jobs':
            return run_list_jobs(args, logger)
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        if getattr(args, 'verbose', False):
            import traceback
            traceback.print_exc()
        return 1

    return 0


def run_simulate(args: 'argparse.Namespace', logger: ActionsLogger) -> int:
    """ワークフロー実行コマンドの処理"""
    workflow_file = Path(args.workflow_file)

    if not workflow_file.exists():
        logger.error(f"ワークフローファイルが見つかりません: {workflow_file}")
        return 1

    logger.info(f"ワークフローを解析中: {workflow_file}")

    # ワークフロー解析
    parser = WorkflowParser()
    try:
        workflow = parser.parse_file(workflow_file)
    except Exception as e:
        logger.error(f"ワークフロー解析エラー: {e}")
        return 1

    # シミュレーター初期化
    simulator = WorkflowSimulator(logger=logger)

    # 環境変数ファイル読み込み
    if args.env_file:
        env_file = Path(args.env_file)
        if env_file.exists():
            simulator.load_env_file(env_file)
        else:
            logger.warning(f"環境変数ファイルが見つかりません: {env_file}")

    # 実行
    if args.dry_run:
        logger.info("ドライランモード: 実際の実行は行いません")
        return simulator.dry_run(workflow, job_name=args.job)
    else:
        return simulator.run(workflow, job_name=args.job)


def run_validate(args: 'argparse.Namespace', logger: ActionsLogger) -> int:
    """ワークフロー検証コマンドの処理"""
    workflow_file = Path(args.workflow_file)

    if not workflow_file.exists():
        logger.error(f"ワークフローファイルが見つかりません: {workflow_file}")
        return 1

    logger.info(f"ワークフロー検証中: {workflow_file}")

    # ワークフロー解析・検証
    parser = WorkflowParser()
    try:
        workflow = parser.parse_file(workflow_file)

        if args.strict:
            # 厳密な検証
            parser.strict_validate(workflow)

        logger.success("ワークフローの検証が完了しました ✓")
        return 0

    except Exception as e:
        logger.error(f"ワークフロー検証エラー: {e}")
        return 1


def run_list_jobs(args: 'argparse.Namespace', logger: ActionsLogger) -> int:
    """ジョブ一覧表示コマンドの処理"""
    workflow_file = Path(args.workflow_file)

    if not workflow_file.exists():
        logger.error(f"ワークフローファイルが見つかりません: {workflow_file}")
        return 1

    # ワークフロー解析
    parser = WorkflowParser()
    try:
        workflow = parser.parse_file(workflow_file)
    except Exception as e:
        logger.error(f"ワークフロー解析エラー: {e}")
        return 1

    jobs = workflow.get('jobs', {})

    if args.format == 'json':
        # JSON形式で出力
        jobs_info = []
        for job_id, job_data in jobs.items():
            jobs_info.append({
                'id': job_id,
                'name': job_data.get('name', job_id),
                'runs_on': job_data.get('runs-on', 'unknown'),
                'steps': len(job_data.get('steps', []))
            })
        print(json.dumps(jobs_info, indent=2, ensure_ascii=False))
    else:
        # テーブル形式で出力
        logger.info(f"ワークフロー: {workflow.get('name', 'Unnamed')}")
        logger.info("=" * 60)
        for job_id, job_data in jobs.items():
            job_name = job_data.get('name', job_id)
            runs_on = job_data.get('runs-on', 'unknown')
            steps_count = len(job_data.get('steps', []))

            print(f"Job ID: {job_id}")
            print(f"  Name: {job_name}")
            print(f"  Runs on: {runs_on}")
            print(f"  Steps: {steps_count}")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
