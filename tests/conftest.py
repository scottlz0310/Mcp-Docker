"""
pytest設定とフィクスチャ

このファイルはpytestの設定とテスト全体で共有されるフィクスチャを定義します。
"""

import os
from typing import Any

import pytest


def pytest_xdist_auto_num_workers(config: Any) -> int | None:  # noqa: ARG001
    """
    pytest-xdistの自動ワーカー数を物理コア数に設定

    デフォルトではautoは論理コア数を使用しますが、
    この関数で物理コア数に変更できます。

    Args:
        config: pytest設定オブジェクト（未使用）

    Returns:
        ワーカー数（Noneの場合はデフォルト動作）
    """
    # 環境変数で明示的に指定されている場合はそちらを優先
    if "PYTEST_XDIST_WORKER_COUNT" in os.environ:
        try:
            return int(os.environ["PYTEST_XDIST_WORKER_COUNT"])
        except ValueError:
            pass

    # デフォルト: 論理コア数を使用（最高のパフォーマンス）
    return None  # Noneを返すとpytest-xdistのデフォルト動作


def pytest_collection_modifyitems(
    config: Any,
    items: list[pytest.Item],  # noqa: ARG001
) -> None:
    """
    テスト収集後にマーカーに基づいてタイムアウトを設定

    ディレクトリ構造に基づいて自動的にマーカーを付与：
    - tests/unit/: unit マーカー（30秒タイムアウト）
    - tests/integration/: integration マーカー（60秒タイムアウト）
    - tests/e2e/: e2e マーカー（300秒タイムアウト）
    - slow マーカーが明示的に付与されている: 600秒タイムアウト

    Args:
        config: pytest設定オブジェクト
        items: 収集されたテストアイテムのリスト
    """
    for item in items:
        # ファイルパスに基づいて自動的にマーカーを付与
        test_path = str(item.fspath)

        if "/tests/unit/" in test_path and "unit" not in item.keywords:
            item.add_marker(pytest.mark.unit)
        elif "/tests/integration/" in test_path and "integration" not in item.keywords:
            item.add_marker(pytest.mark.integration)
        elif "/tests/e2e/" in test_path and "e2e" not in item.keywords:
            item.add_marker(pytest.mark.e2e)

        # マーカーに基づいてタイムアウトを設定
        if "unit" in item.keywords:
            item.add_marker(pytest.mark.timeout(30))
        elif "integration" in item.keywords:
            item.add_marker(pytest.mark.timeout(60))
        elif "e2e" in item.keywords:
            item.add_marker(pytest.mark.timeout(300))
        elif "slow" in item.keywords:
            item.add_marker(pytest.mark.timeout(600))


def pytest_configure(config: Any) -> None:
    """
    pytest設定時に実行される

    e2eテストではxdistを無効化または制限する
    """
    # config.argsまたはinvocation_dirからe2eディレクトリを検出
    is_e2e = False

    # コマンドライン引数をチェック
    if config.args:
        is_e2e = any("/e2e/" in str(arg) or "e2e" in str(arg) for arg in config.args)

    # カレントディレクトリがe2eの場合
    if not is_e2e and hasattr(config, "invocation_params"):
        invocation_dir = str(config.invocation_params.dir)
        is_e2e = "/e2e" in invocation_dir or invocation_dir.endswith("/e2e")

    if is_e2e:
        # xdistを無効化
        if hasattr(config.option, "numprocesses"):
            config.option.numprocesses = 0  # 0で無効化
            config.option.dist = "no"
