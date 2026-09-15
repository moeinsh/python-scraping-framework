"""Demo spider 3: JavaScript-rendered quotes via Playwright.

http://quotes.toscrape.com/js/ loads its quotes with JavaScript, so plain
HTTP fetching returns an empty page. This spider overrides `fetch()` to
render the page in headless Chromium first — everything else (rate
limiting, retries, pipelines, stats) is inherited from BaseSpider.
"""
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from ..core import BaseSpider
from .quotes import parse_quotes


class JSQuotesSpider(BaseSpider):
    name = "js_quotes"
    start_urls = ["http://quotes.toscrape.com/js/"]
    fields = ["text", "author", "tags", "page_url"]

    def __init__(self, config):
        super().__init__(config)
        self._pw = None
        self._browser = None

    def _ensure_browser(self):
        if self._browser is None:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(
                headless=self.config.get("playwright_headless", True)
            )

    def fetch(self, url):
        """Render the page with headless Chromium and return the final DOM."""
        self._rate_limit(url)
        self._ensure_browser()
        context = self._browser.new_context(
            user_agent=self._pick_user_agent()
        )
        try:
            page = context.new_page()
            page.goto(url, timeout=self.config.get("playwright_timeout_ms", 30000))
            page.wait_for_selector("div.quote", timeout=15000)
            self.stats.requests += 1
            return page.content()
        except Exception as exc:  # noqa: BLE001
            self.stats.errors += 1
            print(f"  [error] {url}: {exc}")
            return None
        finally:
            context.close()

    def parse_page(self, html, url):
        soup = BeautifulSoup(html, "html.parser")
        items = parse_quotes(soup, url)
        next_urls = []
        nxt = soup.select_one("li.next a")
        if nxt and nxt.get("href"):
            next_urls.append(urljoin(url, nxt["href"]))
        return items, next_urls

    def close(self):
        if self._browser is not None:
            self._browser.close()
        if self._pw is not None:
            self._pw.stop()
