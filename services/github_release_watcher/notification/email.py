"""
Email (SMTP) 通知
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, cast

from .base import NotificationBase, NotificationMessage


class EmailNotification(NotificationBase):
    """Email (SMTP) 通知"""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        smtp_server_value = config.get("smtp_server")
        self.smtp_port = cast(int, config.get("smtp_port", 587))
        self.username = config.get("username")
        self.password = config.get("password")
        from_addr_value = config.get("from", self.username)
        to_addrs_value = config.get("to", [])
        self.use_tls = cast(bool, config.get("use_tls", True))
        self.use_ssl = cast(bool, config.get("use_ssl", False))

        if not smtp_server_value:
            raise ValueError("SMTP server is required")
        self.smtp_server: str = cast(str, smtp_server_value)

        if not to_addrs_value:
            raise ValueError("Email 'to' address is required")
        if isinstance(to_addrs_value, str):
            self.to_addrs: list[str] = [to_addrs_value]
        else:
            self.to_addrs = cast(list[str], to_addrs_value)

        self.from_addr: str = cast(str, from_addr_value if from_addr_value else self.username)

    def send(self, message: NotificationMessage) -> bool:
        """
        Email通知を送信

        Args:
            message: 通知メッセージ

        Returns:
            送信成功フラグ
        """
        if not self.is_enabled():
            return False

        try:
            # メッセージ作成
            msg = self._build_email_message(message)

            # SMTP接続
            server: smtplib.SMTP | smtplib.SMTP_SSL
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)

            try:
                if self.use_tls and not self.use_ssl:
                    server.starttls()

                # 認証
                if self.username and self.password:
                    server.login(self.username, self.password)

                # 送信
                server.send_message(msg)
                return True

            finally:
                server.quit()

        except Exception as e:
            print(f"Error sending email notification: {e}")
            return False

    def _build_email_message(self, message: NotificationMessage) -> MIMEMultipart:
        """
        Emailメッセージを構築

        Args:
            message: 通知メッセージ

        Returns:
            MIMEメッセージ
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.title
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)

        # プレーンテキスト版
        text_body = self._build_text_body(message)
        msg.attach(MIMEText(text_body, "plain"))

        # HTML版
        html_body = self._build_html_body(message)
        msg.attach(MIMEText(html_body, "html"))

        return msg

    def _build_text_body(self, message: NotificationMessage) -> str:
        """
        プレーンテキストメールボディを構築

        Args:
            message: 通知メッセージ

        Returns:
            テキストボディ
        """
        lines = [
            message.title,
            "=" * len(message.title),
            "",
            message.body,
            "",
        ]

        if message.owner and message.repo:
            lines.append(f"Repository: {message.owner}/{message.repo}")
            lines.append(f"URL: https://github.com/{message.owner}/{message.repo}")

        if message.version:
            lines.append(f"Version: {message.version}")

        if message.release_name:
            lines.append(f"Release: {message.release_name}")

        if message.url:
            lines.append(f"Release URL: {message.url}")

        if message.published_at:
            lines.append(f"Published: {message.published_at}")

        return "\n".join(lines)

    def _build_html_body(self, message: NotificationMessage) -> str:
        """
        HTMLメールボディを構築

        Args:
            message: 通知メッセージ

        Returns:
            HTMLボディ
        """
        html = f"""
        <html>
          <head>
            <style>
              body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
              .header {{ background-color: #0366d6; color: white; padding: 20px; }}
              .content {{ padding: 20px; }}
              .info {{ background-color: #f6f8fa; padding: 15px; margin: 15px 0; border-radius: 6px; }}
              .info-item {{ margin: 10px 0; }}
              .label {{ font-weight: bold; color: #586069; }}
              a {{ color: #0366d6; text-decoration: none; }}
              a:hover {{ text-decoration: underline; }}
            </style>
          </head>
          <body>
            <div class="header">
              <h2>{message.title}</h2>
            </div>
            <div class="content">
              <p>{message.body}</p>
              <div class="info">
        """

        if message.owner and message.repo:
            repo_url = f"https://github.com/{message.owner}/{message.repo}"
            html += f"""
                <div class="info-item">
                  <span class="label">Repository:</span>
                  <a href="{repo_url}">{message.owner}/{message.repo}</a>
                </div>
            """

        if message.version:
            html += f"""
                <div class="info-item">
                  <span class="label">Version:</span> {message.version}
                </div>
            """

        if message.release_name:
            html += f"""
                <div class="info-item">
                  <span class="label">Release:</span> {message.release_name}
                </div>
            """

        if message.url:
            html += f"""
                <div class="info-item">
                  <span class="label">Release URL:</span>
                  <a href="{message.url}">{message.url}</a>
                </div>
            """

        if message.published_at:
            html += f"""
                <div class="info-item">
                  <span class="label">Published:</span> {message.published_at}
                </div>
            """

        html += """
              </div>
            </div>
          </body>
        </html>
        """

        return html
