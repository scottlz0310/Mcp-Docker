#!/usr/bin/env python3
"""
MCP DateTime Validator Server
ファイル保存時に日付フォーマットを自動検証・修正する常駐サービス
"""
import re
import datetime
from pathlib import Path
from typing import Dict, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
import argparse
import time

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DateTimeValidator:
    """日付フォーマット検証・修正クラス"""

    # 日付パターンの定義
    DATE_PATTERNS = {
        # 不正確な可能性が高いパターン
        'suspicious': [
            r'2025-01-\d{2}',  # 2025年1月は疑わしい
            r'2024-12-\d{2}',  # 2024年12月も疑わしい
            r'実行日時\s*\n\s*2025-01-\d{2}',  # 実行日時の直後
        ],
        # 正しい日付フォーマット
        'valid': [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
            r'\d{4}年\d{1,2}月\d{1,2}日',  # 日本語形式
        ]
    }

    def __init__(self):
        self.current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.corrections_made = 0

    def validate_file(self, file_path: Path) -> Dict[str, any]:
        """ファイルの日付を検証し、必要に応じて修正"""
        if not file_path.suffix.lower() in ['.md', '.txt', '.py', '.json', '.js', '.ts']:
            return {'status': 'skipped', 'reason': 'unsupported_format'}

        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content

            # 疑わしい日付パターンをチェック
            issues_found = []
            for pattern in self.DATE_PATTERNS['suspicious']:
                matches = re.findall(pattern, content)
                if matches:
                    issues_found.extend(matches)

            if not issues_found:
                return {'status': 'valid', 'issues': []}

            # 自動修正を試行
            corrected_content = self._auto_correct_dates(content)

            if corrected_content != original_content:
                # バックアップ作成
                backup_path = file_path.with_suffix(f'{file_path.suffix}.bak')
                backup_path.write_text(original_content, encoding='utf-8')

                # 修正版を保存
                file_path.write_text(corrected_content, encoding='utf-8')
                self.corrections_made += 1

                logger.info(f"📅 日付修正完了: {file_path} ({', '.join(issues_found)} → {self.current_date})")

                return {
                    'status': 'corrected',
                    'issues': issues_found,
                    'backup': str(backup_path),
                    'corrections': self.corrections_made
                }
            else:
                return {
                    'status': 'issues_found',
                    'issues': issues_found,
                    'message': '自動修正できませんでした'
                }

        except Exception as e:
            logger.error(f"ファイル処理エラー: {file_path} - {e}")
            return {'status': 'error', 'error': str(e)}

    def _auto_correct_dates(self, content: str) -> str:
        """日付の自動修正"""
        corrected = content

        # 実行日時の修正
        corrected = re.sub(
            r'(実行日時\s*\n\s*)2025-01-\d{2}',
            r'\g<1>' + self.current_date,
            corrected
        )

        # 一般的な疑わしい日付の修正
        corrected = re.sub(
            r'2025-01-\d{2}',
            self.current_date,
            corrected
        )

        corrected = re.sub(
            r'2024-12-\d{2}',
            self.current_date,
            corrected
        )

        return corrected

class DateTimeValidatorHandler(FileSystemEventHandler):
    """ファイルシステム監視ハンドラー"""

    def __init__(self, validator: DateTimeValidator):
        self.validator = validator

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # 特定のディレクトリのみ監視
        if any(part in file_path.parts for part in ['.git', '__pycache__', '.venv', 'node_modules']):
            return

        # バックアップファイルは無視
        if file_path.suffix == '.bak':
            return

        logger.info(f"🔍 ファイル変更検出: {file_path}")
        result = self.validator.validate_file(file_path)

        if result['status'] == 'corrected':
            logger.warning(f"📅 日付修正実行: {file_path}")
        elif result['status'] == 'issues_found':
            logger.warning(f"⚠️ 日付問題検出: {file_path} - {result['issues']}")

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='DateTime Validator MCP Server')
    parser.add_argument('--directory', '-d', default='/workspace', help='監視ディレクトリ')
    parser.add_argument('--validate-only', '-v', action='store_true', help='一括検証のみ実行')

    args = parser.parse_args()

    validator = DateTimeValidator()
    watch_directory = Path(args.directory).resolve()

    if args.validate_only:
        logger.info("プロジェクト全体の日付検証を開始...")
        total_files = 0
        issues_found = 0
        corrections_made = 0

        for file_path in watch_directory.rglob("*"):
            if file_path.is_file():
                total_files += 1
                result = validator.validate_file(file_path)

                if result['status'] in ['issues_found', 'corrected']:
                    issues_found += 1
                    if result['status'] == 'corrected':
                        corrections_made += 1

        logger.info(f"検証完了: {total_files}ファイル, {issues_found}問題, {corrections_made}修正")
    else:
        handler = DateTimeValidatorHandler(validator)
        observer = Observer()
        observer.schedule(handler, str(watch_directory), recursive=True)
        observer.start()

        logger.info(f"🔍 DateTime Validator Server 開始: {watch_directory}")
        logger.info(f"📅 現在日時: {validator.current_date}")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            logger.info(f"📅 DateTime Validator Server 停止 (修正回数: {validator.corrections_made})")

        observer.join()

if __name__ == "__main__":
    main()
