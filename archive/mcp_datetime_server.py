#!/usr/bin/env python3
"""
真のMCP DateTime Server
MCPプロトコルに準拠した日付検証サーバー
"""

import asyncio
from datetime import datetime
from mcp.server import Server

# MCPサーバー初期化
server = Server("datetime-validator")


@server.tool()
async def get_current_date() -> str:
    """現在の日付を取得"""
    return datetime.now().strftime("%Y-%m-%d")


@server.tool()
async def validate_date_in_text(text: str) -> dict:
    """テキスト内の日付を検証"""
    import re

    suspicious_patterns = [
        r"2025-01-\d{2}",
        r"2024-12-\d{2}",
    ]

    issues = []
    for pattern in suspicious_patterns:
        matches = re.findall(pattern, text)
        if matches:
            issues.extend(matches)

    current_date = datetime.now().strftime("%Y-%m-%d")

    return {"current_date": current_date, "suspicious_dates": issues, "needs_correction": len(issues) > 0}


@server.tool()
async def auto_correct_dates(text: str) -> str:
    """テキスト内の日付を自動修正"""
    import re

    current_date = datetime.now().strftime("%Y-%m-%d")
    corrected = text

    # 疑わしい日付を現在日付に置換
    corrected = re.sub(r"2025-01-\d{2}", current_date, corrected)
    corrected = re.sub(r"2024-12-\d{2}", current_date, corrected)

    return corrected


async def main():
    """MCPサーバー起動"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
