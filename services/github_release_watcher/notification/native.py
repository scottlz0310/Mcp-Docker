"""
ネイティブ通知 - Windows Toast/macOS/Linux
"""

import platform

from .base import NotificationBase, NotificationMessage


class NativeNotification(NotificationBase):
    """プラットフォーム別ネイティブ通知"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.system = platform.system()
        self.duration = config.get("duration", 10)
        self.sound = config.get("sound", True)

    def send(self, message: NotificationMessage) -> bool:
        """
        プラットフォームに応じた通知を送信

        Args:
            message: 通知メッセージ

        Returns:
            送信成功フラグ
        """
        if not self.is_enabled():
            return False

        try:
            if self.system == "Windows":
                return self._send_windows(message)
            elif self.system == "Darwin":  # macOS
                return self._send_macos(message)
            elif self.system == "Linux":
                return self._send_linux(message)
            else:
                print(f"Unsupported platform: {self.system}")
                return False
        except Exception as e:
            print(f"Error sending native notification: {e}")
            return False

    def _send_windows(self, message: NotificationMessage) -> bool:
        """
        Windows Toast通知を送信

        Args:
            message: 通知メッセージ

        Returns:
            送信成功フラグ
        """
        try:
            from win10toast import ToastNotifier

            toaster = ToastNotifier()
            toaster.show_toast(
                message.title,
                message.body,
                duration=self.duration,
                threaded=True,
            )
            return True
        except ImportError:
            print("win10toast not installed. Install with: pip install win10toast")
            return False
        except Exception as e:
            print(f"Error sending Windows toast: {e}")
            return False

    def _send_macos(self, message: NotificationMessage) -> bool:
        """
        macOS通知を送信

        Args:
            message: 通知メッセージ

        Returns:
            送信成功フラグ
        """
        try:
            import pync

            # サウンド設定
            sound = "default" if self.sound else None

            pync.notify(
                message.body,
                title=message.title,
                sound=sound,
                open_url=message.url,
            )
            return True
        except ImportError:
            print("pync not installed. Install with: pip install pync")
            return False
        except Exception as e:
            print(f"Error sending macOS notification: {e}")
            return False

    def _send_linux(self, message: NotificationMessage) -> bool:
        """
        Linux通知を送信（libnotify経由）

        Args:
            message: 通知メッセージ

        Returns:
            送信成功フラグ
        """
        try:
            from plyer import notification

            notification.notify(
                title=message.title,
                message=message.body,
                timeout=self.duration,
            )
            return True
        except ImportError:
            print("plyer not installed. Install with: pip install plyer")
            return False
        except Exception as e:
            print(f"Error sending Linux notification: {e}")
            return False
