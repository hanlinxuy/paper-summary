"""Browser lifecycle management with context reuse"""

import atexit
import logging
from contextlib import contextmanager
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

logger = logging.getLogger(__name__)

# Global browser manager instance
_browser_manager: Optional["BrowserManager"] = None


class BrowserManager:
    """Manages Playwright browser instance with context reuse"""

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        proxy: str = "",
    ):
        self.headless = headless
        self.timeout = timeout
        self.user_agent = user_agent
        self.proxy = proxy
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page_count = 0

    @property
    def is_initialized(self) -> bool:
        return self._browser is not None

    def initialize(self) -> None:
        """Initialize browser instance"""
        if self.is_initialized:
            return

        logger.info("Initializing Playwright browser...")
        self._playwright = sync_playwright().start()

        # Ignore SSL certificate errors for corporate proxy
        # Disable GPU, X11, and other GUI-related features for headless/WSL

        launch_kwargs = {
            "headless": self.headless,
            "args": [
                "--ignore-certificate-errors",
                "--disable-setuid-sandbox",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--no-zygote",
                "--single-process",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-sync",
                "--disable-translate",
                "--metrics-recording-only",
                "--mute-audio",
                "--safebrowsing-disable-auto-update",
                "--disable-component-update",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
            ],
        }

        # Add proxy if configured
        if self.proxy:
            launch_kwargs["proxy"] = {"server": self.proxy}

        self._browser = self._playwright.chromium.launch(**launch_kwargs)
        self._context = self._browser.new_context(
            user_agent=self.user_agent,
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True,
        )

        # Register cleanup on exit
        atexit.register(self.close)

        logger.info("Browser initialized successfully")

    def new_page(self) -> Page:
        """Create a new page from the shared context"""
        if not self.is_initialized:
            self.initialize()

        self._page_count += 1
        page = self._context.new_page()

        # Set default timeout
        page.set_default_timeout(self.timeout)

        return page

    def close(self) -> None:
        """Close browser and cleanup resources"""
        if self._browser:
            logger.info(f"Closing browser (created {self._page_count} pages)")
            self._browser.close()
            self._browser = None
            self._context = None

        if self._playwright:
            self._playwright.stop()
            self._playwright = None

        global _browser_manager
        _browser_manager = None

    @contextmanager
    def page_context(self):
        """Context manager for page operations"""
        page = self.new_page()
        try:
            yield page
        finally:
            page.close()

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - keep browser open for reuse"""
        pass


def get_browser_manager(
    headless: bool = True,
    timeout: int = 30000,
    proxy: str = "",
) -> BrowserManager:
    """Get or create global browser manager instance"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager(
            headless=headless,
            timeout=timeout,
            proxy=proxy,
        )
    return _browser_manager
