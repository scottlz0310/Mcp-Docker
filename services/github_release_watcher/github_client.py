"""
GitHub API クライアント - 非同期API呼び出しとキャッシュ対応
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

import aiohttp
from cachetools import TTLCache  # type: ignore[import-untyped]


class GitHubClient:
    """非同期GitHub APIクライアント"""

    def __init__(self, token: Optional[str] = None, cache_ttl: int = 300):
        """
        Args:
            token: GitHub APIトークン
            cache_ttl: キャッシュTTL（秒）
        """
        self.token = token
        self.base_url = "https://api.github.com"
        self.cache = TTLCache(maxsize=100, ttl=cache_ttl)
        self.rate_limit_remaining: Optional[int] = None
        self.rate_limit_reset: Optional[int] = None

    def _get_headers(self) -> dict[str, str]:
        """APIリクエストヘッダーを取得"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Release-Watcher",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    async def _check_rate_limit_async(self) -> None:
        """レート制限をチェックし、必要に応じて待機"""
        if self.rate_limit_remaining is not None and self.rate_limit_remaining == 0:
            if self.rate_limit_reset:
                now = datetime.now(timezone.utc)
                reset_time = datetime.fromtimestamp(self.rate_limit_reset, timezone.utc)
                wait_seconds = (reset_time - now).total_seconds()

                if wait_seconds > 0:
                    print(f"Rate limit exceeded. Waiting {wait_seconds:.0f} seconds until reset...")
                    await asyncio.sleep(wait_seconds + 1)

    def _update_rate_limit(self, headers: dict) -> None:
        """レート制限情報を更新"""
        if "X-RateLimit-Remaining" in headers:
            self.rate_limit_remaining = int(headers["X-RateLimit-Remaining"])
        if "X-RateLimit-Reset" in headers:
            self.rate_limit_reset = int(headers["X-RateLimit-Reset"])

    async def get_latest_release_async(self, owner: str, repo: str, use_cache: bool = True) -> Optional[dict]:
        """
        最新リリースを非同期取得

        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            use_cache: キャッシュを使用するか

        Returns:
            リリース情報辞書、またはNone
        """
        cache_key = f"{owner}/{repo}/latest"

        # キャッシュチェック
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]

        # レート制限チェック
        await self._check_rate_limit_async()

        url = f"{self.base_url}/repos/{owner}/{repo}/releases/latest"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._get_headers()) as response:
                self._update_rate_limit(dict(response.headers))

                if response.status == 404:
                    # リリースが存在しない
                    return None
                elif response.status != 200:
                    print(f"Error fetching release for {owner}/{repo}: {response.status}")
                    return None

                data = await response.json()

                # キャッシュに保存
                self.cache[cache_key] = data
                return data

    async def get_releases_async(
        self,
        owner: str,
        repo: str,
        per_page: int = 10,
        use_cache: bool = True,
    ) -> list[dict]:
        """
        リリース一覧を非同期取得

        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            per_page: ページあたりの件数
            use_cache: キャッシュを使用するか

        Returns:
            リリース情報リスト
        """
        cache_key = f"{owner}/{repo}/releases/{per_page}"

        # キャッシュチェック
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]

        # レート制限チェック
        await self._check_rate_limit_async()

        url = f"{self.base_url}/repos/{owner}/{repo}/releases"
        params = {"per_page": per_page}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._get_headers(), params=params) as response:
                self._update_rate_limit(dict(response.headers))

                if response.status != 200:
                    print(f"Error fetching releases for {owner}/{repo}: {response.status}")
                    return []

                data = await response.json()

                # キャッシュに保存
                self.cache[cache_key] = data
                return data

    async def check_multiple_repos_async(self, repos: list[dict]) -> list[tuple[dict, Optional[dict]]]:
        """
        複数リポジトリを並列チェック

        Args:
            repos: リポジトリ設定リスト

        Returns:
            (リポジトリ設定, リリース情報) のタプルリスト
        """
        tasks = []
        for repo_config in repos:
            owner = repo_config["owner"]
            repo = repo_config["repo"]
            task = self.get_latest_release_async(owner, repo)
            tasks.append((repo_config, task))

        results = []
        for repo_config, task in tasks:
            release = await task
            results.append((repo_config, release))

        return results

    async def get_rate_limit_async(self) -> dict:
        """
        レート制限情報を取得

        Returns:
            レート制限情報辞書
        """
        url = f"{self.base_url}/rate_limit"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    return await response.json()
                return {}
