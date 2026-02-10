"""Base Scraper with retry logic and caching"""

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all scrapers with caching and retry support"""

    def __init__(
        self,
        browser_manager: "BrowserManager",
        cache_dir: Optional[Path] = None,
        cache_ttl: int = 86400,  # 24 hours
        timeout: int = 30000,
    ):
        self.browser_manager = browser_manager
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        self.timeout = timeout

    def _get_cache_path(self, url: str) -> Path:
        """Generate cache file path from URL"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.json"

    def _get_cached(self, url: str) -> Optional[Any]:
        """Load cached data if available and not expired"""
        if not self.cache_dir or not self.cache_dir.exists():
            return None

        cache_path = self._get_cache_path(url)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)

            import time

            if time.time() - cached.get("timestamp", 0) > self.cache_ttl:
                return None

            return cached.get("data")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to read cache: {e}")
            return None

    def _save_cache(self, url: str, data: Any) -> None:
        """Save data to cache"""
        if not self.cache_dir:
            return

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self._get_cache_path(url)

        try:
            cached = {
                "timestamp": __import__("time").time(),
                "url": url,
                "data": data,
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cached, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.warning(f"Failed to save cache: {e}")

    def _get_page(self, url: str, use_cache: bool = True) -> Any:
        """Get page content with caching and retry"""
        # Try cache first
        if use_cache:
            cached = self._get_cached(url)
            if cached is not None:
                logger.info(f"Cache hit: {url}")
                return cached

        # Fetch from browser
        return self._fetch_page(url)

    @abstractmethod
    def _fetch_page(self, url: str) -> Any:
        """Fetch page content using Playwright - implement in subclasses"""
        pass

    def scrape(self, url: str, use_cache: bool = True) -> Any:
        """Public method to scrape a URL with retry and caching"""
        return self._get_page(url, use_cache=use_cache)


class ScraperWithRetry(BaseScraper):
    """Base scraper with built-in retry logic"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_page(self, url: str) -> Any:
        """Fetch with automatic retry on failure"""
        return super()._fetch_page(url)
