#!/usr/bin/env python3
"""
GitHub Actions Simulator - プラットフォーム対応テスト

このテストスイートは、各プラットフォームでの GitHub Actions Simulator の
動作を検証します。
"""

import os
import platform
import subprocess
import unittest
from pathlib import Path
from conftest import PROJECT_ROOT
from typing import Dict, List, Optional, Tuple


class PlatformSupportTest(unittest.TestCase):
    """プラットフォーム対応のテストクラス"""

    @classmethod
    def setUpClass(cls):
        """テストクラスの初期化"""
        # tests/integration から 2つ上がプロジェクトルート
        cls.project_root = PROJECT_ROOT
        cls.scripts_dir = cls.project_root / "scripts"
        cls.platform_info = cls._get_platform_info()

    @classmethod
    def _get_platform_info(cls) -> Dict[str, str]:
        """プラットフォーム情報を取得"""
        system = platform.system().lower()

        info = {
            "system": system,
            "machine": platform.machine(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        }

        if system == "linux":
            try:
                # ディストリビューション情報を取得
                result = subprocess.run(["lsb_release", "-a"], capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    info["distro"] = result.stdout
                else:
                    # /etc/os-release から取得
                    try:
                        with open("/etc/os-release", "r") as f:
                            info["distro"] = f.read()
                    except FileNotFoundError:
                        info["distro"] = "Unknown"
            except FileNotFoundError:
                info["distro"] = "Unknown"

        elif system == "darwin":
            try:
                result = subprocess.run(["sw_vers"], capture_output=True, text=True, check=True)
                info["macos_version"] = result.stdout
            except (subprocess.CalledProcessError, FileNotFoundError):
                info["macos_version"] = "Unknown"

        elif system == "windows":
            info["windows_version"] = platform.win32_ver()

        return info

    def _run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """コマンドを実行して結果を返す"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5分のタイムアウト
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)

    @unittest.skip("旧実装に依存 - Phase 4で削除された機能")
    def test_platform_detection(self):
        """プラットフォーム検出のテスト"""
        script_path = self.scripts_dir / "run-actions.sh"
        self.assertTrue(script_path.exists(), "run-actions.sh が見つかりません")

        # プラットフォーム検出機能をテスト
        returncode, stdout, stderr = self._run_command(["bash", str(script_path), "--check-deps"])

        # 基本的な出力確認
        self.assertIn("プラットフォーム:", stdout, "プラットフォーム情報が出力されていません")

        # プラットフォーム固有の確認
        system = self.platform_info["system"]
        if system == "linux":
            # Linux の場合、"ubuntu", "fedora", "linux" のいずれかが検出されればOK
            linux_platforms = ["ubuntu", "fedora", "arch", "opensuse", "linux"]
            found_linux = any(platform in stdout.lower() for platform in linux_platforms)
            self.assertTrue(
                found_linux,
                f"Linux プラットフォームが検出されていません。出力: {stdout}",
            )
        elif system == "darwin":
            self.assertIn("macos", stdout.lower(), "macOS プラットフォームが検出されていません")
        elif system == "windows":
            self.assertIn(
                "windows",
                stdout.lower(),
                "Windows プラットフォームが検出されていません",
            )

    @unittest.skip("旧実装に依存 - Phase 4で削除された機能")
    def test_extended_dependency_check(self):
        """拡張依存関係チェックのテスト"""
        script_path = self.scripts_dir / "run-actions.sh"

        returncode, stdout, stderr = self._run_command(["bash", str(script_path), "--check-deps-extended"])

        # 拡張チェックの出力確認
        self.assertIn("拡張依存関係チェック", stdout, "拡張チェックが実行されていません")
        self.assertIn("プラットフォーム固有の最適化提案", stdout, "最適化提案が表示されていません")
        self.assertIn("システムリソース情報", stdout, "システムリソース情報が表示されていません")

    def test_platform_specific_installer_exists(self):
        """プラットフォーム固有のインストーラーの存在確認"""
        system = self.platform_info["system"]

        if system == "linux":
            installer_path = self.scripts_dir / "install-linux.sh"
            self.assertTrue(installer_path.exists(), "Linux インストーラーが見つかりません")
            self.assertTrue(
                os.access(installer_path, os.X_OK),
                "Linux インストーラーが実行可能ではありません",
            )

        elif system == "darwin":
            installer_path = self.scripts_dir / "install-macos.sh"
            self.assertTrue(installer_path.exists(), "macOS インストーラーが見つかりません")
            self.assertTrue(
                os.access(installer_path, os.X_OK),
                "macOS インストーラーが実行可能ではありません",
            )

        elif system == "windows":
            installer_path = self.scripts_dir / "install-windows.ps1"
            self.assertTrue(installer_path.exists(), "Windows インストーラーが見つかりません")

    def test_unified_installer_exists(self):
        """統合インストーラーの存在確認"""
        installer_path = self.scripts_dir / "install.sh"
        self.assertTrue(installer_path.exists(), "統合インストーラーが見つかりません")
        self.assertTrue(
            os.access(installer_path, os.X_OK),
            "統合インストーラーが実行可能ではありません",
        )

    def test_platform_documentation_exists(self):
        """プラットフォームドキュメントの存在確認"""
        platform_doc = self.project_root / "docs" / "PLATFORM_SUPPORT.md"
        assert platform_doc.exists(), "PLATFORM_SUPPORT.mdが存在しません"

        content = platform_doc.read_text()
        # 基本的なセクションの存在確認
        assert "# プラットフォームサポート" in content
        assert "## サポート対象プラットフォーム" in content
