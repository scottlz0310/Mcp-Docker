"""
バージョン比較とリリースフィルタリング機能
"""

import re
from typing import Optional
from packaging import version


class ReleaseComparator:
    """リリースバージョンの比較とフィルタリング"""

    def is_newer(self, current: str, latest: str) -> bool:
        """
        最新バージョンが現在のバージョンより新しいかチェック

        Args:
            current: 現在のバージョン文字列
            latest: 最新のバージョン文字列

        Returns:
            最新バージョンが新しい場合True
        """
        try:
            # packagingライブラリでセマンティックバージョニング対応
            return version.parse(latest) > version.parse(current)
        except Exception:
            # パース失敗時は文字列比較にフォールバック
            return latest > current

    def filter_releases(
        self,
        releases: list[dict],
        filter_mode: str = "stable",
        version_pattern: Optional[str] = None,
    ) -> list[dict]:
        """
        リリースをフィルタリング

        Args:
            releases: リリース情報のリスト
            filter_mode: フィルタモード ("all", "stable", "prerelease")
            version_pattern: バージョンパターン（正規表現）

        Returns:
            フィルタリングされたリリースリスト
        """
        filtered = releases

        # フィルタモードによるフィルタリング
        if filter_mode == "stable":
            filtered = [r for r in filtered if not r.get("prerelease", False)]
        elif filter_mode == "prerelease":
            filtered = [r for r in filtered if r.get("prerelease", False)]
        # "all" の場合はフィルタリングしない

        # バージョンパターンによるフィルタリング
        if version_pattern:
            pattern = re.compile(version_pattern)
            filtered = [r for r in filtered if pattern.match(r.get("tag_name", ""))]

        return filtered

    def extract_version(self, tag_name: str) -> str:
        """
        タグ名からバージョン文字列を抽出

        Args:
            tag_name: GitHubタグ名
                例: "v1.2.3", "1.2.3", "linux-msft-wsl-6.6.87.2"

        Returns:
            バージョン文字列（例: "1.2.3", "6.6.87.2"）
        """
        # パターン1: linux-msft-wsl-X.X.X.X 形式（WSL2-Linux-Kernel）
        wsl_match = re.search(r"linux-msft-wsl-([\d.]+)", tag_name)
        if wsl_match is not None:
            return wsl_match.group(1)

        # パターン2: 先頭の "v" を削除（一般的なタグ）
        if tag_name.startswith("v"):
            return tag_name[1:]

        # パターン3: そのまま返す
        return tag_name
