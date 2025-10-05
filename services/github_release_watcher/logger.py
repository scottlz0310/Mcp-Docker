"""
ロギング設定
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "github-release-watcher",
    level: str = "INFO",
    log_file: Optional[Path] = None,
    log_format: Optional[str] = None,
) -> logging.Logger:
    """
    ロガーをセットアップ

    Args:
        name: ロガー名
        level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_file: ログファイルパス（指定時はファイル出力も行う）
        log_format: ログフォーマット

    Returns:
        設定済みロガー
    """
    logger = logging.getLogger(name)

    # 既存のハンドラーをクリア
    logger.handlers.clear()

    # ログレベル設定
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # ログフォーマット
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(log_format)

    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ファイルハンドラー（指定時）
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 上位ロガーへの伝播を無効化（重複ログ防止）
    logger.propagate = False

    return logger


def get_logger(name: str = "github-release-watcher") -> logging.Logger:
    """
    既存のロガーを取得

    Args:
        name: ロガー名

    Returns:
        ロガー
    """
    return logging.getLogger(name)
