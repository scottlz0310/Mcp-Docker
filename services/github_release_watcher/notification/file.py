"""
ファイル出力通知 (JSON/Markdown)
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from .base import NotificationBase, NotificationMessage


class FileNotification(NotificationBase):
    """ファイル出力通知"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.output_path = config.get("output_path")
        self.format = config.get("format", "json")  # "json" or "markdown"
        self.append = config.get("append", True)

        if not self.output_path:
            raise ValueError("File output_path is required")

        self.output_path = Path(self.output_path)

    def send(self, message: NotificationMessage) -> bool:
        """
        ファイルに通知を出力

        Args:
            message: 通知メッセージ

        Returns:
            出力成功フラグ
        """
        if not self.is_enabled():
            return False

        try:
            # ディレクトリ作成
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            # フォーマットに応じて出力
            if self.format == "json":
                return self._write_json(message)
            elif self.format == "markdown":
                return self._write_markdown(message)
            else:
                print(f"Unsupported file format: {self.format}")
                return False

        except Exception as e:
            print(f"Error writing to file: {e}")
            return False

    def _write_json(self, message: NotificationMessage) -> bool:
        """
        JSON形式で出力

        Args:
            message: 通知メッセージ

        Returns:
            出力成功フラグ
        """
        # メッセージデータを辞書化
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": message.title,
            "body": message.body,
            "owner": message.owner,
            "repo": message.repo,
            "version": message.version,
            "release_name": message.release_name,
            "url": message.url,
            "published_at": message.published_at,
        }

        if self.append and self.output_path.exists():
            # 既存のJSONファイルに追記
            with open(self.output_path, encoding="utf-8") as f:
                try:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
                except json.JSONDecodeError:
                    existing_data = []

            existing_data.append(data)

            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
        else:
            # 新規作成または上書き
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump([data], f, indent=2, ensure_ascii=False)

        return True

    def _write_markdown(self, message: NotificationMessage) -> bool:
        """
        Markdown形式で出力

        Args:
            message: 通知メッセージ

        Returns:
            出力成功フラグ
        """
        # Markdownコンテンツ生成
        timestamp = datetime.now(timezone.utc).isoformat()
        md_content = f"""
## {message.title}

**Date:** {timestamp}

{message.body}

"""

        if message.owner and message.repo:
            repo_url = f"https://github.com/{message.owner}/{message.repo}"
            md_content += f"**Repository:** [{message.owner}/{message.repo}]({repo_url})\n\n"

        if message.version:
            md_content += f"**Version:** {message.version}\n\n"

        if message.release_name:
            md_content += f"**Release:** {message.release_name}\n\n"

        if message.url:
            md_content += f"**Release URL:** [{message.url}]({message.url})\n\n"

        if message.published_at:
            md_content += f"**Published:** {message.published_at}\n\n"

        md_content += "---\n\n"

        if self.append and self.output_path.exists():
            # 追記モード
            with open(self.output_path, "a", encoding="utf-8") as f:
                f.write(md_content)
        else:
            # 新規作成または上書き
            header = "# GitHub Release Notifications\n\n"
            with open(self.output_path, "w", encoding="utf-8") as f:
                f.write(header)
                f.write(md_content)

        return True
