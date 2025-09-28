#!/usr/bin/env python3
"""
現在の日付を取得するユーティリティ
AIが正確な日付を取得するために使用
"""

import datetime


def get_current_date() -> str:
    """現在の日付を YYYY-MM-DD 形式で返す"""
    return datetime.datetime.now().strftime("%Y-%m-%d")


def get_current_datetime() -> str:
    """現在の日時を ISO 8601 形式で返す"""
    return datetime.datetime.now().isoformat()


if __name__ == "__main__":
    print(get_current_date())
