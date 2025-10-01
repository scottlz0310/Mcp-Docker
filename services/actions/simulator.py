"""
レガシー スタブ - 組み込みワークフロー シミュレーターの削除

このプロジェクトは現在、act エンジンのみに依存しています。このモジュールをインポートすることは
後方互換性のために可能ですが、レガシー シミュレーターのインスタンス化を試みると
``RuntimeError`` が発生し、非推奨であることが明確に説明されます。
"""

from __future__ import annotations


class SimulationError(RuntimeError):
    """後方互換性のために保持されます。"""


class WorkflowSimulator:  # pragma: no cover - legacy shim
    """呼び出し元に削除について通知するプレースホルダー。"""

    def __init__(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:  # pragma: no cover - legacy shim
        raise RuntimeError(
            "組み込みのワークフロー シミュレーターは削除されました。代わりに act エンジンを使用してください。"
        )

    def __getattr__(self, _name: str) -> None:
        raise RuntimeError(
            "組み込みのワークフロー シミュレーターは削除されました。代わりに act エンジンを使用してください。"
        )
