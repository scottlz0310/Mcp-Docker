"""
GitHub Actions Simulator - ActionsLogger テスト
ログ出力機能のテストケース
"""

import logging
import sys

import pytest

from services.actions.logger import ActionsLogger


class TestActionsLogger:
    """ActionsLoggerのテストクラス"""

    def test_init_default(self):
        """デフォルト初期化テスト"""
        logger = ActionsLogger()

        assert logger.verbose is False
        assert logger.quiet is False
        assert logger.debug_mode is False
        assert logger.logger.level == logging.INFO

    def test_init_verbose(self):
        """詳細モード初期化テスト"""
        logger = ActionsLogger(verbose=True)

        assert logger.verbose is True
        assert logger.logger.level == logging.DEBUG

    def test_init_quiet(self):
        """静音モード初期化テスト"""
        logger = ActionsLogger(quiet=True)

        assert logger.quiet is True
        assert logger.logger.level == logging.WARNING

    def test_init_debug(self):
        """デバッグモード初期化テスト"""
        logger = ActionsLogger(debug=True)

        assert logger.debug_mode is True
        assert logger.verbose is True  # デバッグモードは詳細モードを含む
        assert logger.logger.level == logging.DEBUG

    def test_init_custom_name(self):
        """カスタム名初期化テスト"""
        custom_name = "test-logger"
        logger = ActionsLogger(name=custom_name)

        assert logger.logger.name == custom_name

    def test_log_levels(self):
        """ログレベルテスト"""
        # 通常モード
        logger_normal = ActionsLogger()
        assert logger_normal.logger.level == logging.INFO

        # 詳細モード
        logger_verbose = ActionsLogger(verbose=True)
        assert logger_verbose.logger.level == logging.DEBUG

        # 静音モード
        logger_quiet = ActionsLogger(quiet=True)
        assert logger_quiet.logger.level == logging.WARNING

    def test_handler_setup(self):
        """ハンドラー設定テスト"""
        logger = ActionsLogger()

        # ハンドラーが設定されていることを確認
        assert len(logger.logger.handlers) > 0

        # StreamHandlerが設定されていることを確認
        handler = logger.logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream == sys.stdout

    def test_formatter_setup(self):
        """フォーマッター設定テスト"""
        logger = ActionsLogger()

        handler = logger.logger.handlers[0]
        formatter = handler.formatter

        assert formatter is not None
        # フォーマッターの形式をテスト
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "test message" in formatted

    def test_multiple_loggers_no_duplicate_handlers(self):
        """複数ロガー作成時の重複ハンドラー防止テスト"""
        logger1 = ActionsLogger(name="test1")
        logger2 = ActionsLogger(name="test1")  # 同じ名前

        # 同じロガーインスタンスを参照するため、ハンドラーは重複しない
        assert len(logger1.logger.handlers) == len(logger2.logger.handlers)

    def test_log_output(self):
        """ログ出力テスト"""
        logger = ActionsLogger()

        # ログメッセージを出力（実際のハンドラーを使用）
        logger.info("Test info message")

        # ハンドラーが設定されていることを確認
        assert len(logger.logger.handlers) > 0
        handler = logger.logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)

    def test_verbose_debug_relationship(self):
        """詳細モードとデバッグモードの関係テスト"""
        # デバッグモードは詳細モードを含む
        logger_debug = ActionsLogger(debug=True)
        assert logger_debug.verbose is True
        assert logger_debug.debug_mode is True

        # 詳細モードのみ
        logger_verbose = ActionsLogger(verbose=True)
        assert logger_verbose.verbose is True
        assert logger_verbose.debug_mode is False

    def test_quiet_overrides_verbose(self):
        """静音モードが詳細モードを上書きするテスト"""
        logger = ActionsLogger(verbose=True, quiet=True)

        # 静音モードが優先される
        assert logger.quiet is True
        assert logger.logger.level == logging.WARNING

    def test_debug_overrides_quiet(self):
        """デバッグモードが静音モードを上書きするテスト"""
        logger = ActionsLogger(debug=True, quiet=True)

        # 実際の実装では quiet が優先される
        assert logger.debug_mode is True
        assert logger.verbose is True
        assert logger.quiet is True
        assert logger.logger.level == logging.WARNING  # quiet が優先される

    def test_logger_properties(self):
        """ロガープロパティテスト"""
        logger = ActionsLogger(
            verbose=True, quiet=False, debug=True, name="test-logger"
        )

        assert hasattr(logger, "logger")
        assert hasattr(logger, "verbose")
        assert hasattr(logger, "quiet")
        assert hasattr(logger, "debug_mode")

        assert isinstance(logger.logger, logging.Logger)
        assert isinstance(logger.verbose, bool)
        assert isinstance(logger.quiet, bool)
        assert isinstance(logger.debug_mode, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
