"""
GitHub Actions Simulator - Output テスト
出力管理機能のテストケース
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from services.actions.output import get_output_root, ensure_subdir


class TestOutputModule:
    """Outputモジュールのテストクラス"""

    def test_get_output_root_default(self):
        """デフォルト出力ルート取得テスト"""
        with patch.dict(os.environ, {}, clear=True):
            # 環境変数がない場合のデフォルト動作
            root = get_output_root()

            assert isinstance(root, Path)
            assert root.exists()
            assert root.is_dir()

    def test_get_output_root_with_env_var(self):
        """環境変数指定出力ルート取得テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_output_dir = Path(temp_dir) / "test_output"

            with patch.dict(
                os.environ, {"MCP_ACTIONS_OUTPUT_DIR": str(test_output_dir)}
            ):
                root = get_output_root()

                assert root == test_output_dir.resolve()
                assert root.exists()
                assert root.is_dir()

    def test_get_output_root_with_tilde_expansion(self):
        """チルダ展開テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # ホームディレクトリをモック
            with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                test_path = "~/test_output"

                with patch.dict(os.environ, {"MCP_ACTIONS_OUTPUT_DIR": test_path}):
                    root = get_output_root()

                    expected_path = Path(temp_dir) / "test_output"
                    assert root == expected_path.resolve()
                    assert root.exists()

    def test_get_output_root_permission_fallback(self):
        """権限エラー時のフォールバック動作テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 権限エラーをシミュレート
            with patch(
                "pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")
            ):
                with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                    root = get_output_root()

                    # フォールバックパスが使用される
                    expected_fallback = (
                        Path(temp_dir) / ".cache" / "mcp-docker" / "actions"
                    )
                    assert root == expected_fallback
                    assert root.exists()

    def test_ensure_subdir_single_segment(self):
        """単一セグメントサブディレクトリ作成テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"MCP_ACTIONS_OUTPUT_DIR": temp_dir}):
                subdir = ensure_subdir("test_subdir")

                expected_path = Path(temp_dir) / "test_subdir"
                assert subdir == expected_path
                assert subdir.exists()
                assert subdir.is_dir()

    def test_ensure_subdir_multiple_segments(self):
        """複数セグメントサブディレクトリ作成テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"MCP_ACTIONS_OUTPUT_DIR": temp_dir}):
                subdir = ensure_subdir("level1", "level2", "level3")

                expected_path = Path(temp_dir) / "level1" / "level2" / "level3"
                assert subdir == expected_path
                assert subdir.exists()
                assert subdir.is_dir()

    def test_ensure_subdir_with_iterable(self):
        """イテラブルセグメントサブディレクトリ作成テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"MCP_ACTIONS_OUTPUT_DIR": temp_dir}):
                segments = ["part1", "part2", "part3"]
                subdir = ensure_subdir(segments)

                expected_path = Path(temp_dir) / "part1" / "part2" / "part3"
                assert subdir == expected_path
                assert subdir.exists()
                assert subdir.is_dir()

    def test_ensure_subdir_mixed_segments(self):
        """混合セグメントサブディレクトリ作成テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"MCP_ACTIONS_OUTPUT_DIR": temp_dir}):
                subdir = ensure_subdir("base", ["sub1", "sub2"], "final")

                expected_path = Path(temp_dir) / "base" / "sub1" / "sub2" / "final"
                assert subdir == expected_path
                assert subdir.exists()
                assert subdir.is_dir()

    def test_ensure_subdir_empty_segments(self):
        """空セグメント処理テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"MCP_ACTIONS_OUTPUT_DIR": temp_dir}):
                subdir = ensure_subdir("", "valid", "", "segment")

                # 空のセグメントは無視される
                expected_path = Path(temp_dir) / "valid" / "segment"
                assert subdir == expected_path
                assert subdir.exists()
                assert subdir.is_dir()

    def test_ensure_subdir_already_exists(self):
        """既存ディレクトリの処理テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"MCP_ACTIONS_OUTPUT_DIR": temp_dir}):
                # 最初の作成
                subdir1 = ensure_subdir("existing_dir")
                assert subdir1.exists()

                # 同じディレクトリを再度作成
                subdir2 = ensure_subdir("existing_dir")
                assert subdir2 == subdir1
                assert subdir2.exists()

    def test_ensure_subdir_nested_creation(self):
        """ネストしたディレクトリ作成テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"MCP_ACTIONS_OUTPUT_DIR": temp_dir}):
                # 深いネストのディレクトリを作成
                deep_segments = ["a", "b", "c", "d", "e", "f"]
                subdir = ensure_subdir(*deep_segments)

                expected_path = Path(temp_dir)
                for segment in deep_segments:
                    expected_path = expected_path / segment

                assert subdir == expected_path
                assert subdir.exists()
                assert subdir.is_dir()

    def test_ensure_subdir_with_special_characters(self):
        """特殊文字を含むディレクトリ名テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"MCP_ACTIONS_OUTPUT_DIR": temp_dir}):
                # 特殊文字を含むディレクトリ名（ただし、OSで有効なもの）
                special_name = "test-dir_123"
                subdir = ensure_subdir(special_name)

                expected_path = Path(temp_dir) / special_name
                assert subdir == expected_path
                assert subdir.exists()
                assert subdir.is_dir()

    def test_path_resolution(self):
        """パス解決テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 相対パスを含む環境変数
            relative_path = os.path.join(temp_dir, ".", "output")

            with patch.dict(os.environ, {"MCP_ACTIONS_OUTPUT_DIR": relative_path}):
                root = get_output_root()

                # パスが正規化されていることを確認
                assert root.is_absolute()
                assert ".." not in str(root)
                assert "/." not in str(root)

    def test_concurrent_directory_creation(self):
        """並行ディレクトリ作成テスト"""
        import threading

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"MCP_ACTIONS_OUTPUT_DIR": temp_dir}):
                results = []

                def create_subdir(name):
                    try:
                        subdir = ensure_subdir(f"concurrent_{name}")
                        results.append(subdir)
                    except Exception as e:
                        results.append(e)

                # 複数スレッドで同時にディレクトリを作成
                threads = []
                for i in range(5):
                    thread = threading.Thread(target=create_subdir, args=(i,))
                    threads.append(thread)
                    thread.start()

                for thread in threads:
                    thread.join()

                # 全てのスレッドが成功することを確認
                assert len(results) == 5
                for result in results:
                    assert isinstance(result, Path)
                    assert result.exists()

    def test_output_root_consistency(self):
        """出力ルートの一貫性テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"MCP_ACTIONS_OUTPUT_DIR": temp_dir}):
                # 複数回呼び出しても同じパスが返される
                root1 = get_output_root()
                root2 = get_output_root()
                root3 = get_output_root()

                assert root1 == root2 == root3
                assert root1.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
