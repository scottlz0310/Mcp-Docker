"""
状態管理 - スレッドセーフなJSON状態保存
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional


class StateManager:
    """スレッドセーフな状態管理"""

    def __init__(self, state_file: Path):
        """
        Args:
            state_file: 状態ファイルのパス
        """
        self.state_file = state_file
        self.lock = Lock()
        self.state = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        """状態ファイルを読み込み"""
        if not self.state_file.exists():
            return {"repositories": {}, "last_check": None}

        try:
            with open(self.state_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load state file: {e}")
            return {"repositories": {}, "last_check": None}

    def _save_state(self) -> None:
        """状態ファイルに保存"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error: Failed to save state file: {e}")

    def get_latest_version(self, repo_url: str) -> Optional[str]:
        """
        リポジトリの最新バージョンを取得

        Args:
            repo_url: リポジトリURL

        Returns:
            最新バージョン文字列、または None
        """
        with self.lock:
            repo_state = self.state["repositories"].get(repo_url, {})
            return repo_state.get("latest_version")

    def update_latest_version(
        self,
        repo_url: str,
        version: str,
        channels: list[str],
        metadata: Optional[dict] = None,
    ) -> None:
        """
        リポジトリの最新バージョンを更新

        Args:
            repo_url: リポジトリURL
            version: バージョン文字列
            channels: 通知チャネルリスト
            metadata: 追加メタデータ
        """
        with self.lock:
            now = datetime.now(timezone.utc).isoformat()

            if repo_url not in self.state["repositories"]:
                self.state["repositories"][repo_url] = {}

            self.state["repositories"][repo_url].update(
                {
                    "latest_version": version,
                    "last_updated": now,
                    "notification_channels": channels,
                    "metadata": metadata or {},
                }
            )

            self.state["last_check"] = now
            self._save_state()

    def get_notification_history(self, repo_url: str) -> list[dict]:
        """
        通知履歴を取得

        Args:
            repo_url: リポジトリURL

        Returns:
            通知履歴リスト
        """
        with self.lock:
            repo_state = self.state["repositories"].get(repo_url, {})
            return repo_state.get("notification_history", [])

    def add_notification_history(self, repo_url: str, version: str, channels: list[str], success: bool) -> None:
        """
        通知履歴を追加

        Args:
            repo_url: リポジトリURL
            version: バージョン文字列
            channels: 通知チャネルリスト
            success: 通知成功フラグ
        """
        with self.lock:
            if repo_url not in self.state["repositories"]:
                self.state["repositories"][repo_url] = {}

            if "notification_history" not in self.state["repositories"][repo_url]:
                self.state["repositories"][repo_url]["notification_history"] = []

            history_entry = {
                "version": version,
                "channels": channels,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "success": success,
            }

            self.state["repositories"][repo_url]["notification_history"].append(history_entry)

            # 履歴は最新10件のみ保持
            self.state["repositories"][repo_url]["notification_history"] = self.state["repositories"][repo_url][
                "notification_history"
            ][-10:]

            self._save_state()

    def get_all_repositories(self) -> dict[str, dict]:
        """
        全リポジトリの状態を取得

        Returns:
            リポジトリ状態の辞書
        """
        with self.lock:
            return self.state["repositories"].copy()

    def reset_repository(self, repo_url: str) -> None:
        """
        リポジトリの状態をリセット

        Args:
            repo_url: リポジトリURL
        """
        with self.lock:
            if repo_url in self.state["repositories"]:
                del self.state["repositories"][repo_url]
                self._save_state()
