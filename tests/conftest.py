"""pytest共通設定 - プロジェクトルート取得を一元化"""

import sys
from pathlib import Path


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

    raise RuntimeError(f"プロジェクトルートが見つかりません（開始: {start_path}）")


# グローバル変数として公開
PROJECT_ROOT = find_project_root()

# Pythonパスに追加（絶対インポートを可能にする）
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
