"""
GitHub Release Watcher - Comparator ユニットテスト
"""

from services.github_release_watcher.comparator import ReleaseComparator


class TestReleaseComparator:
    """ReleaseComparator のテスト"""

    def test_is_newer_with_semantic_versions(self):
        """セマンティックバージョニングでの比較"""
        comparator = ReleaseComparator()

        # 基本的な比較
        assert comparator.is_newer("1.0.0", "1.0.1")
        assert comparator.is_newer("1.0.0", "1.1.0")
        assert comparator.is_newer("1.0.0", "2.0.0")

        # 同じバージョン
        assert not comparator.is_newer("1.0.0", "1.0.0")

        # 古いバージョン
        assert not comparator.is_newer("1.1.0", "1.0.0")
        assert not comparator.is_newer("2.0.0", "1.0.0")

    def test_is_newer_with_v_prefix(self):
        """v プレフィックス付きバージョンでの比較"""
        comparator = ReleaseComparator()

        assert comparator.is_newer("v1.0.0", "v1.0.1")
        assert comparator.is_newer("1.0.0", "v1.0.1")
        assert comparator.is_newer("v1.0.0", "1.0.1")

    def test_is_newer_with_prerelease(self):
        """プレリリースバージョンでの比較"""
        comparator = ReleaseComparator()

        assert comparator.is_newer("1.0.0-alpha", "1.0.0-beta")
        assert comparator.is_newer("1.0.0-beta", "1.0.0")
        assert comparator.is_newer("1.0.0", "1.0.1-alpha")

    def test_is_newer_fallback_to_string_comparison(self):
        """パース失敗時の文字列比較フォールバック"""
        comparator = ReleaseComparator()

        # 非標準のバージョン文字列
        assert comparator.is_newer("abc", "def")
        assert not comparator.is_newer("def", "abc")

    def test_filter_releases_stable_only(self):
        """安定版のみフィルタリング"""
        comparator = ReleaseComparator()

        releases = [
            {"tag_name": "v1.0.0", "prerelease": False},
            {"tag_name": "v1.1.0-beta", "prerelease": True},
            {"tag_name": "v1.2.0", "prerelease": False},
        ]

        filtered = comparator.filter_releases(releases, filter_mode="stable")

        assert len(filtered) == 2
        assert all(not r.get("prerelease") for r in filtered)

    def test_filter_releases_prerelease_only(self):
        """プレリリースのみフィルタリング"""
        comparator = ReleaseComparator()

        releases = [
            {"tag_name": "v1.0.0", "prerelease": False},
            {"tag_name": "v1.1.0-beta", "prerelease": True},
            {"tag_name": "v1.2.0", "prerelease": False},
        ]

        filtered = comparator.filter_releases(releases, filter_mode="prerelease")

        assert len(filtered) == 1
        assert all(r.get("prerelease") for r in filtered)

    def test_filter_releases_all(self):
        """全リリースを返す"""
        comparator = ReleaseComparator()

        releases = [
            {"tag_name": "v1.0.0", "prerelease": False},
            {"tag_name": "v1.1.0-beta", "prerelease": True},
            {"tag_name": "v1.2.0", "prerelease": False},
        ]

        filtered = comparator.filter_releases(releases, filter_mode="all")

        assert len(filtered) == 3

    def test_filter_releases_with_version_pattern(self):
        """バージョンパターンでフィルタリング"""
        comparator = ReleaseComparator()

        releases = [
            {"tag_name": "v1.0.0", "prerelease": False},
            {"tag_name": "v2.0.0", "prerelease": False},
            {"tag_name": "v2.1.0", "prerelease": False},
        ]

        # v2.x.x のみ
        filtered = comparator.filter_releases(releases, filter_mode="all", version_pattern=r"^v2\.")

        assert len(filtered) == 2
        assert all(r["tag_name"].startswith("v2.") for r in filtered)

    def test_extract_version(self):
        """バージョン文字列の抽出"""
        comparator = ReleaseComparator()

        assert comparator.extract_version("v1.2.3") == "1.2.3"
        assert comparator.extract_version("1.2.3") == "1.2.3"
        assert comparator.extract_version("v1.0.0-beta") == "1.0.0-beta"

    def test_extract_version_without_v_prefix(self):
        """v プレフィックスなしのバージョン"""
        comparator = ReleaseComparator()

        assert comparator.extract_version("1.2.3") == "1.2.3"
        assert comparator.extract_version("2023.01.15") == "2023.01.15"

    def test_extract_version_wsl_kernel_format(self):
        """WSL2-Linux-Kernel タグ形式からのバージョン抽出"""
        comparator = ReleaseComparator()

        # linux-msft-wsl-X.X.X.X 形式
        assert comparator.extract_version("linux-msft-wsl-6.6.87.2") == "6.6.87.2"
        assert comparator.extract_version("linux-msft-wsl-6.6.87.1") == "6.6.87.1"
        assert comparator.extract_version("linux-msft-wsl-6.6.84.1") == "6.6.84.1"
        assert comparator.extract_version("linux-msft-wsl-6.6.75.3") == "6.6.75.3"

    def test_is_newer_with_wsl_kernel_versions(self):
        """WSL2カーネルバージョンでの比較"""
        comparator = ReleaseComparator()

        # 4セグメントバージョン番号の比較
        assert comparator.is_newer("6.6.84.1", "6.6.87.1")
        assert comparator.is_newer("6.6.87.1", "6.6.87.2")
        assert comparator.is_newer("6.6.75.3", "6.6.87.2")

        # 同じバージョン
        assert not comparator.is_newer("6.6.87.2", "6.6.87.2")

        # 古いバージョン
        assert not comparator.is_newer("6.6.87.2", "6.6.87.1")
