#!/usr/bin/env python3
"""
Docker統合テストの実行例
DockerIntegrationCheckerの実際の動作を確認するためのスクリプト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# ruff: noqa: E402
from services.actions.docker_integration_checker import DockerIntegrationChecker
from services.actions.logger import ActionsLogger


def main():
    """Docker統合テストのメイン関数"""
    print("🐳 Docker統合テストを開始します...")
    print("=" * 60)

    # ロガーを初期化
    logger = ActionsLogger(verbose=True)

    # Docker統合チェッカーを初期化
    checker = DockerIntegrationChecker(logger=logger)

    try:
        # 1. Dockerソケットアクセステスト
        print("\n📡 1. Dockerソケットアクセステスト")
        print("-" * 40)
        socket_result = checker.verify_socket_access()
        print(f"結果: {'✅ 成功' if socket_result else '❌ 失敗'}")

        # 2. コンテナ通信テスト
        print("\n🔄 2. コンテナ通信テスト")
        print("-" * 40)
        comm_result = checker.test_container_communication()
        print(f"結果: {'✅ 成功' if comm_result.success else '❌ 失敗'}")
        print(f"メッセージ: {comm_result.message}")
        if comm_result.execution_time_ms:
            print(f"実行時間: {comm_result.execution_time_ms:.1f}ms")

        # 3. act-Docker互換性テスト
        print("\n🔧 3. act-Docker互換性テスト")
        print("-" * 40)
        compat_result = checker.check_act_docker_compatibility()
        print(f"結果: {'✅ 互換性あり' if compat_result.compatible else '❌ 互換性なし'}")
        print(f"メッセージ: {compat_result.message}")
        if compat_result.act_version:
            print(f"actバージョン: {compat_result.act_version}")
        if compat_result.docker_version:
            print(f"Dockerバージョン: {compat_result.docker_version}")

        if compat_result.issues:
            print("問題:")
            for issue in compat_result.issues:
                print(f"  - {issue}")

        if compat_result.recommendations:
            print("推奨事項:")
            for rec in compat_result.recommendations:
                print(f"  - {rec}")

        # 4. Docker daemon接続テスト（リトライ付き）
        print("\n🔌 4. Docker daemon接続テスト（リトライ付き）")
        print("-" * 40)
        daemon_result = checker.test_docker_daemon_connection_with_retry()
        print(f"結果: {daemon_result.status.value}")
        print(f"メッセージ: {daemon_result.message}")
        if daemon_result.response_time_ms:
            print(f"応答時間: {daemon_result.response_time_ms:.1f}ms")

        # 5. 包括的Dockerチェック
        print("\n🔍 5. 包括的Dockerチェック")
        print("-" * 40)
        comprehensive_result = checker.run_comprehensive_docker_check()
        print(f"全体結果: {'✅ 成功' if comprehensive_result['overall_success'] else '❌ 失敗'}")
        print(f"サマリー: {comprehensive_result['summary']}")

        # 修正推奨事項の表示
        if not comprehensive_result["overall_success"]:
            print("\n🛠️ 修正推奨事項:")
            print("-" * 40)
            recommendations = checker.generate_docker_fix_recommendations(comprehensive_result)
            for rec in recommendations:
                print(f"  {rec}")

        # 最終結果
        print("\n" + "=" * 60)
        if comprehensive_result["overall_success"]:
            print("🎉 Docker統合テスト完了: 全て正常!")
            print("GitHub Actions Simulatorは正常に動作する準備ができています。")
            return 0
        else:
            print("⚠️ Docker統合テスト完了: 問題が検出されました")
            print("上記の推奨事項に従って問題を修正してください。")
            return 1

    except KeyboardInterrupt:
        print("\n\n⏹️ テストが中断されました")
        return 130
    except Exception as e:
        print(f"\n\n❌ テスト中にエラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
