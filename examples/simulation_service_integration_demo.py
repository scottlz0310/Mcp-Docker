#!/usr/bin/env python3
"""
SimulationService統合デモ

このデモはタスク10の実装を実際に動作させて、
SimulationServiceとEnhancedActWrapperの統合機能を示します。

実装された機能:
1. 実行前診断チェック
2. 詳細結果レポート機能
3. パフォーマンスメトリクスと実行トレースの統合
"""

import sys
import tempfile
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.actions.service import SimulationService, SimulationParameters
from services.actions.logger import ActionsLogger


def create_sample_workflow() -> Path:
    """サンプルワークフローファイルを作成"""
    temp_dir = Path(tempfile.mkdtemp())
    workflow_file = temp_dir / "demo.yml"

    workflow_content = """
name: SimulationService Integration Demo
on: [push, pull_request]

jobs:
  demo-job:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          echo "Installing dependencies..."
          sleep 2
          echo "Dependencies installed successfully"

      - name: Run tests
        run: |
          echo "Running tests..."
          sleep 1
          echo "All tests passed!"

      - name: Build application
        run: |
          echo "Building application..."
          sleep 3
          echo "Build completed successfully"
"""

    workflow_file.write_text(workflow_content.strip())
    return workflow_file


def demo_basic_simulation():
    """基本的なシミュレーション（拡張機能なし）"""
    print("=" * 60)
    print("基本的なSimulationService（拡張機能なし）")
    print("=" * 60)

    logger = ActionsLogger(verbose=True)
    workflow_file = create_sample_workflow()

    # 基本的なSimulationService
    service = SimulationService(
        use_enhanced_wrapper=False,
        enable_diagnostics=False,
        enable_performance_monitoring=False,
    )

    params = SimulationParameters(
        workflow_file=workflow_file,
        verbose=True,
        dry_run=True  # ドライランで実行
    )

    print(f"ワークフローファイル: {workflow_file}")
    print(f"サービス状態: {service.get_simulation_status()}")

    try:
        result = service.run_simulation(params, logger=logger)

        print(f"\n実行結果:")
        print(f"  成功: {result.success}")
        print(f"  終了コード: {result.return_code}")
        print(f"  実行時間: {result.execution_time_ms:.2f}ms")
        print(f"  診断結果数: {len(result.diagnostic_results)}")
        print(f"  パフォーマンスメトリクス: {bool(result.performance_metrics)}")
        print(f"  実行トレース: {bool(result.execution_trace)}")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

    # クリーンアップ
    import shutil
    shutil.rmtree(workflow_file.parent)


def demo_enhanced_simulation():
    """拡張機能付きシミュレーション"""
    print("\n" + "=" * 60)
    print("拡張SimulationService（全機能有効）")
    print("=" * 60)

    logger = ActionsLogger(verbose=True)
    workflow_file = create_sample_workflow()

    # 拡張機能付きSimulationService
    service = SimulationService(
        use_enhanced_wrapper=True,
        enable_diagnostics=True,
        enable_performance_monitoring=True,
        pre_execution_diagnostics=True,
        detailed_result_reporting=True,
    )

    params = SimulationParameters(
        workflow_file=workflow_file,
        verbose=True,
        dry_run=True  # ドライランで実行
    )

    print(f"ワークフローファイル: {workflow_file}")
    print(f"サービス状態: {service.get_simulation_status()}")

    try:
        result = service.run_simulation(params, logger=logger)

        print(f"\n実行結果:")
        print(f"  成功: {result.success}")
        print(f"  終了コード: {result.return_code}")
        print(f"  実行時間: {result.execution_time_ms:.2f}ms")
        print(f"  診断結果数: {len(result.diagnostic_results)}")
        print(f"  パフォーマンスメトリクス: {bool(result.performance_metrics)}")
        print(f"  実行トレース: {bool(result.execution_trace)}")
        print(f"  ボトルネック検出数: {len(result.bottlenecks_detected)}")
        print(f"  最適化機会数: {len(result.optimization_opportunities)}")

        # 詳細情報の表示
        if result.diagnostic_results:
            print(f"\n診断結果の詳細:")
            for i, diag in enumerate(result.diagnostic_results, 1):
                print(f"  {i}. フェーズ: {diag.get('phase', 'unknown')}")
                print(f"     ステータス: {diag.get('results', {}).get('overall_status', 'unknown')}")
                print(f"     サマリー: {diag.get('results', {}).get('summary', 'N/A')}")

        if result.performance_metrics:
            print(f"\nパフォーマンスメトリクス:")
            for key, value in result.performance_metrics.items():
                print(f"  {key}: {value}")

        if result.execution_trace:
            print(f"\n実行トレース:")
            for key, value in result.execution_trace.items():
                print(f"  {key}: {value}")

        if result.metadata:
            print(f"\nメタデータ:")
            for key, value in result.metadata.items():
                if key not in ['command']:  # 長いコマンドは省略
                    print(f"  {key}: {value}")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

    # クリーンアップ
    import shutil
    shutil.rmtree(workflow_file.parent)


def demo_feature_toggle():
    """機能の動的切り替えデモ"""
    print("\n" + "=" * 60)
    print("機能の動的切り替えデモ")
    print("=" * 60)

    logger = ActionsLogger(verbose=True)

    # 初期状態（拡張機能なし）
    service = SimulationService()

    print("初期状態:")
    status = service.get_simulation_status()
    print(f"  拡張ラッパー: {status['enhanced_wrapper_enabled']}")
    print(f"  診断機能: {status['diagnostics_enabled']}")
    print(f"  パフォーマンス監視: {status['performance_monitoring_enabled']}")

    # 拡張機能を有効化
    print("\n拡張機能を有効化...")
    service.enable_enhanced_features(
        enable_diagnostics=True,
        enable_performance_monitoring=True,
        enable_detailed_reporting=True
    )

    print("有効化後:")
    status = service.get_simulation_status()
    print(f"  拡張ラッパー: {status['enhanced_wrapper_enabled']}")
    print(f"  診断機能: {status['diagnostics_enabled']}")
    print(f"  パフォーマンス監視: {status['performance_monitoring_enabled']}")
    print(f"  詳細レポート: {status['detailed_result_reporting_enabled']}")

    # コンポーネントの状態確認
    print(f"\nコンポーネント状態:")
    components = status.get('components', {})
    for name, available in components.items():
        print(f"  {name}: {'利用可能' if available else '利用不可'}")


def main():
    """メインデモ実行"""
    print("SimulationService統合デモ")
    print("タスク10: SimulationServiceとの統合")
    print()

    try:
        # 1. 基本的なシミュレーション
        demo_basic_simulation()

        # 2. 拡張機能付きシミュレーション
        demo_enhanced_simulation()

        # 3. 機能の動的切り替え
        demo_feature_toggle()

        print("\n" + "=" * 60)
        print("デモ完了")
        print("=" * 60)
        print()
        print("実装された機能:")
        print("✓ SimulationServiceにEnhancedActWrapperと診断機能を統合")
        print("✓ 実行前診断チェックと詳細結果レポート機能を追加")
        print("✓ パフォーマンスメトリクスと実行トレースの統合を実装")
        print("✓ 既存機能との後方互換性を維持")
        print("✓ 機能の動的有効化/無効化をサポート")

    except KeyboardInterrupt:
        print("\nデモが中断されました")
    except Exception as e:
        print(f"\nデモ実行中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
