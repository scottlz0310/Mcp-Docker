#!/usr/bin/env python3
"""
GitHub Actions Simulator - プラットフォーム対応テスト

このテストスイートは、各プラットフォームでの GitHub Actions Simulator の
動作を検証します。
"""

import os
import platform
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class PlatformSupportTest(unittest.TestCase):
    """プラットフォーム対応のテストクラス"""

    @classmethod
    def setUpClass(cls):
        """テストクラスの初期化"""
        cls.project_root = Path(__file__).parent.parent
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
                result = subprocess.run(
                    ["lsb_release", "-a"], capture_output=True, text=True, check=False
                )
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
                result = subprocess.run(
                    ["sw_vers"], capture_output=True, text=True, check=True
                )
                info["macos_version"] = result.stdout
            except (subprocess.CalledProcessError, FileNotFoundError):
                info["macos_version"] = "Unknown"

        elif system == "windows":
            info["windows_version"] = platform.win32_ver()

        return info

    def _run_command(
        self, cmd: List[str], cwd: Optional[Path] = None
    ) -> Tuple[int, str, str]:
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

    def test_platform_detection(self):
        """プラットフォーム検出のテスト"""
        script_path = self.scripts_dir / "run-actions.sh"
        self.assertTrue(script_path.exists(), "run-actions.sh が見つかりません")

        # プラットフォーム検出機能をテスト
        returncode, stdout, stderr = self._run_command(
            ["bash", str(script_path), "--check-deps"]
        )

        # 基本的な出力確認
        self.assertIn(
            "プラットフォーム:", stdout, "プラットフォーム情報が出力されていません"
        )

        # プラットフォーム固有の確認
        system = self.platform_info["system"]
        if system == "linux":
            # Linux の場合、"ubuntu", "fedora", "linux" のいずれかが検出されればOK
            linux_platforms = ["ubuntu", "fedora", "arch", "opensuse", "linux"]
            found_linux = any(
                platform in stdout.lower() for platform in linux_platforms
            )
            self.assertTrue(
                found_linux,
                f"Linux プラットフォームが検出されていません。出力: {stdout}",
            )
        elif system == "darwin":
            self.assertIn(
                "macos", stdout.lower(), "macOS プラットフォームが検出されていません"
            )
        elif system == "windows":
            self.assertIn(
                "windows",
                stdout.lower(),
                "Windows プラットフォームが検出されていません",
            )

    def test_extended_dependency_check(self):
        """拡張依存関係チェックのテスト"""
        script_path = self.scripts_dir / "run-actions.sh"

        returncode, stdout, stderr = self._run_command(
            ["bash", str(script_path), "--check-deps-extended"]
        )

        # 拡張チェックの出力確認
        self.assertIn(
            "拡張依存関係チェック", stdout, "拡張チェックが実行されていません"
        )
        self.assertIn(
            "プラットフォーム固有の最適化提案", stdout, "最適化提案が表示されていません"
        )
        self.assertIn(
            "システムリソース情報", stdout, "システムリソース情報が表示されていません"
        )

    def test_platform_specific_installer_exists(self):
        """プラットフォーム固有のインストーラーの存在確認"""
        system = self.platform_info["system"]

        if system == "linux":
            installer_path = self.scripts_dir / "install-linux.sh"
            self.assertTrue(
                installer_path.exists(), "Linux インストーラーが見つかりません"
            )
            self.assertTrue(
                os.access(installer_path, os.X_OK),
                "Linux インストーラーが実行可能ではありません",
            )

        elif system == "darwin":
            installer_path = self.scripts_dir / "install-macos.sh"
            self.assertTrue(
                installer_path.exists(), "macOS インストーラーが見つかりません"
            )
            self.assertTrue(
                os.access(installer_path, os.X_OK),
                "macOS インストーラーが実行可能ではありません",
            )

        elif system == "windows":
            installer_path = self.scripts_dir / "install-windows.ps1"
            self.assertTrue(
                installer_path.exists(), "Windows インストーラーが見つかりません"
            )

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
        docs_path = self.project_root / "docs" / "PLATFORM_SUPPORT.md"
        self.assertTrue(
            docs_path.exists(), "プラットフォームサポートドキュメントが見つかりません"
        )

        # ドキュメントの内容確認
        with open(docs_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 必要なセクションの存在確認
        required_sections = [
            "# プラットフォーム対応ガイド",
            "## Linux",
            "## macOS",
            "## Windows (WSL2)",
            "## 共通の最適化設定",
            "## トラブルシューティング",
        ]

        for section in required_sections:
            self.assertIn(
                section, content, f"必要なセクションが見つかりません: {section}"
            )

    def test_docker_availability(self):
        """Docker の利用可能性テスト"""
        # Docker コマンドの存在確認
        returncode, stdout, stderr = self._run_command(["which", "docker"])
        if returncode != 0:
            self.skipTest("Docker がインストールされていません")

        # Docker の動作確認
        returncode, stdout, stderr = self._run_command(["docker", "--version"])
        self.assertEqual(returncode, 0, f"Docker バージョン確認に失敗: {stderr}")

        # Docker サービスの状態確認
        returncode, stdout, stderr = self._run_command(["docker", "info"])
        if returncode != 0:
            self.skipTest(f"Docker サービスが利用できません: {stderr}")

    def test_git_availability(self):
        """Git の利用可能性テスト"""
        returncode, stdout, stderr = self._run_command(["git", "--version"])
        self.assertEqual(returncode, 0, f"Git が利用できません: {stderr}")

        # Git 設定の確認
        returncode, stdout, stderr = self._run_command(["git", "config", "--list"])
        self.assertEqual(returncode, 0, f"Git 設定の確認に失敗: {stderr}")

    def test_uv_availability(self):
        """uv の利用可能性テスト（オプション）"""
        returncode, stdout, stderr = self._run_command(["which", "uv"])
        if returncode != 0:
            self.skipTest("uv がインストールされていません（オプション）")

        returncode, stdout, stderr = self._run_command(["uv", "--version"])
        self.assertEqual(returncode, 0, f"uv バージョン確認に失敗: {stderr}")

    def test_platform_specific_optimizations(self):
        """プラットフォーム固有の最適化確認"""
        system = self.platform_info["system"]

        if system == "linux":
            self._test_linux_optimizations()
        elif system == "darwin":
            self._test_macos_optimizations()
        elif system == "windows":
            self._test_windows_optimizations()

    def _test_linux_optimizations(self):
        """Linux 固有の最適化テスト"""
        # Docker グループの確認
        returncode, stdout, stderr = self._run_command(["groups"])
        if "docker" not in stdout:
            self.skipTest("ユーザーが docker グループに属していません")

        # systemd サービスの確認（利用可能な場合）
        returncode, stdout, stderr = self._run_command(["which", "systemctl"])
        if returncode == 0:
            returncode, stdout, stderr = self._run_command(
                ["systemctl", "is-active", "docker"]
            )
            if returncode != 0:
                self.skipTest(f"Docker サービスが起動していません: {stderr}")

    def _test_macos_optimizations(self):
        """macOS 固有の最適化テスト"""
        # Docker Desktop の確認
        docker_app_path = Path("/Applications/Docker.app")
        if not docker_app_path.exists():
            self.skipTest("Docker Desktop がインストールされていません")

        # Homebrew の確認
        returncode, stdout, stderr = self._run_command(["which", "brew"])
        if returncode == 0:
            # Homebrew のバージョン確認
            returncode, stdout, stderr = self._run_command(["brew", "--version"])
            self.assertEqual(returncode, 0, f"Homebrew の確認に失敗: {stderr}")

    def _test_windows_optimizations(self):
        """Windows 固有の最適化テスト"""
        # WSL 環境での実行確認
        wsl_env = os.environ.get("WSL_DISTRO_NAME")
        if not wsl_env:
            self.skipTest("WSL 環境で実行されていません")

        # Windows パスへのアクセス確認
        windows_path = Path("/mnt/c")
        if windows_path.exists():
            self.assertTrue(
                windows_path.is_dir(), "Windows ファイルシステムにアクセスできません"
            )

    def test_performance_baseline(self):
        """基本的なパフォーマンステスト"""
        if not self._is_docker_available():
            self.skipTest("Docker が利用できません")

        # 簡単な Docker コマンドの実行時間測定
        import time

        start_time = time.time()
        returncode, stdout, stderr = self._run_command(
            ["docker", "run", "--rm", "hello-world"]
        )
        end_time = time.time()

        self.assertEqual(returncode, 0, f"Docker テストコンテナの実行に失敗: {stderr}")

        duration = end_time - start_time
        self.assertLess(
            duration, 60, f"Docker コンテナの実行が遅すぎます: {duration:.2f}秒"
        )

        # プラットフォーム別の期待値
        system = self.platform_info["system"]
        if system == "linux":
            expected_max = 30
        elif system == "darwin":
            expected_max = 45
        elif system == "windows":
            expected_max = 60
        else:
            expected_max = 60

        if duration > expected_max:
            print(
                f"警告: Docker の実行時間が期待値を超えています: {duration:.2f}秒 > {expected_max}秒"
            )

    def _is_docker_available(self) -> bool:
        """Docker が利用可能かチェック"""
        returncode, _, _ = self._run_command(["docker", "info"])
        return returncode == 0

    def test_installer_help_output(self):
        """インストーラーのヘルプ出力テスト"""
        # 統合インストーラーのヘルプ
        installer_path = self.scripts_dir / "install.sh"
        returncode, stdout, stderr = self._run_command(
            ["bash", str(installer_path), "--help"]
        )
        self.assertEqual(returncode, 0, "統合インストーラーのヘルプ表示に失敗")
        self.assertIn("使用方法", stdout, "ヘルプにUsage情報が含まれていません")

        # プラットフォーム固有インストーラーのヘルプ
        system = self.platform_info["system"]
        if system in ["linux", "darwin"]:
            platform_installer = (
                f"install-{system if system != 'darwin' else 'macos'}.sh"
            )
            installer_path = self.scripts_dir / platform_installer

            returncode, stdout, stderr = self._run_command(
                ["bash", str(installer_path), "--help"]
            )
            self.assertEqual(returncode, 0, f"{platform_installer} のヘルプ表示に失敗")
            self.assertIn("使用方法", stdout, "ヘルプにUsage情報が含まれていません")


class PlatformSpecificTest(unittest.TestCase):
    """プラットフォーム固有のテストクラス"""

    def setUp(self):
        """各テストの初期化"""
        self.system = platform.system().lower()
        self.project_root = Path(__file__).parent.parent

    @unittest.skipUnless(platform.system().lower() == "linux", "Linux でのみ実行")
    def test_linux_specific_features(self):
        """Linux 固有機能のテスト"""
        # systemd の確認
        if Path("/bin/systemctl").exists():
            result = subprocess.run(
                ["systemctl", "--version"], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, "systemctl が利用できません")

        # パッケージマネージャーの確認
        package_managers = ["apt", "dnf", "yum", "pacman", "zypper"]
        found_pm = False

        for pm in package_managers:
            if subprocess.run(["which", pm], capture_output=True).returncode == 0:
                found_pm = True
                break

        self.assertTrue(
            found_pm, "サポートされているパッケージマネージャーが見つかりません"
        )

    @unittest.skipUnless(platform.system().lower() == "darwin", "macOS でのみ実行")
    def test_macos_specific_features(self):
        """macOS 固有機能のテスト"""
        # macOS バージョンの確認
        result = subprocess.run(
            ["sw_vers", "-productVersion"], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, "macOS バージョンの取得に失敗")

        version = result.stdout.strip()
        major_version = int(version.split(".")[0])
        self.assertGreaterEqual(
            major_version, 12, f"macOS 12.0 以降が必要です。現在: {version}"
        )

        # Homebrew の確認（インストールされている場合）
        result = subprocess.run(["which", "brew"], capture_output=True)
        if result.returncode == 0:
            result = subprocess.run(
                ["brew", "--version"], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, "Homebrew の確認に失敗")

    @unittest.skipUnless(
        "microsoft" in platform.uname().release.lower(), "WSL でのみ実行"
    )
    def test_wsl_specific_features(self):
        """WSL 固有機能のテスト"""
        # WSL 環境変数の確認
        wsl_distro = os.environ.get("WSL_DISTRO_NAME")
        self.assertIsNotNone(wsl_distro, "WSL_DISTRO_NAME 環境変数が設定されていません")

        # Windows ファイルシステムへのアクセス確認
        windows_root = Path("/mnt/c")
        self.assertTrue(
            windows_root.exists(), "Windows ファイルシステムにアクセスできません"
        )

        # WSL バージョンの確認
        wsl_version = os.environ.get("WSL_INTEROP")
        self.assertIsNotNone(
            wsl_version, "WSL_INTEROP が設定されていません（WSL2 が必要）"
        )


def main():
    """メイン関数"""
    # テストの実行前に環境情報を表示
    print("=" * 60)
    print("GitHub Actions Simulator - プラットフォーム対応テスト")
    print("=" * 60)
    print(f"プラットフォーム: {platform.platform()}")
    print(f"Python バージョン: {platform.python_version()}")
    print(f"アーキテクチャ: {platform.machine()}")
    print("=" * 60)
    print()

    # テストスイートの作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # テストクラスを追加
    suite.addTests(loader.loadTestsFromTestCase(PlatformSupportTest))
    suite.addTests(loader.loadTestsFromTestCase(PlatformSpecificTest))

    # テストの実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 結果の表示
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ すべてのテストが成功しました！")
        return 0
    else:
        print(
            f"❌ {len(result.failures)} 個の失敗、{len(result.errors)} 個のエラーが発生しました"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
