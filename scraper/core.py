"""Framework core: spider base class + run statistics.

Anti-blocking features live here so every spider gets them for free:
  * rotating User-Agents (fresh identity per request)
  * per-domain rate limiting (minimum gap between requests to one host)
  * retries with exponential backoff on transient failures
  * optional proxy rotation (disabled by default, enabled via config.yaml)
"""
import json
import os
import random
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests


class RunStats:
    """Per-run counters, serialised to runs/ as JSON when the crawl ends."""

    def __init__(self, spider_name):
        self.spider_name = spider_name
        self.started_at = datetime.now(timezone.utc)
        self.requests = 0
        self.items = 0
        self.errors = 0
        self.finished_at = None

    def to_dict(self):
        finished = self.finished_at or datetime.now(timezone.utc)
        return {
            "spider": self.spider_name,
            "started_at": self.started_at.isoformat(),
            "finished_at": finished.isoformat(),
            "duration_seconds": round((finished - self.started_at).total_seconds(), 1),
            "requests": self.requests,
            "items": self.items,
            "errors": self.errors,
        }

    def save(self, runs_dir):
        os.makedirs(runs_dir, exist_ok=True)
        stamp = self.started_at.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(runs_dir, f"{self.spider_name}_{stamp}.json")
        self.finished_at = datetime.now(timezone.utc)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path


class BaseSpider:
    """Base class for all spiders.

    Subclasses set:
        name        -- unique spider name (used for output files)
        start_urls  -- list of seed URLs
        fields      -- ordered list of output field names

    and implement:
        parse_page(html, url) -> (items, next_urls)
            items:     list of dicts (keys should match `fields`)
            next_urls: list of absolute URLs to crawl next (pagination, ...)
    """

    name = "base"
    start_urls = []
    fields = []

    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.user_agents = config["user_agents"]
        self.min_gap = float(config.get("rate_limit_seconds", 1.0))
        self.max_retries = int(config.get("max_retries", 3))
        self.backoff_base = float(config.get("backoff_base", 2.0))
        self.timeout = int(config.get("request_timeout", 20))
        self.proxies_enabled = bool(config.get("proxies_enabled", False))
        self.proxies = config.get("proxies") or []
        self._last_request = {}          # domain -> timestamp of last request
        self.stats = RunStats(self.name)

    # ── anti-blocking helpers ──────────────────────────────────────────
    def _pick_user_agent(self):
        return random.choice(self.user_agents)

    def _pick_proxy(self):
        if self.proxies_enabled and self.proxies:
            proxy = random.choice(self.proxies)
            return {"http": proxy, "https": proxy}
        return None

    def _rate_limit(self, url):
        """Sleep so that requests to the same domain are spaced out."""
        domain = urlparse(url).netloc
        last = self._last_request.get(domain, 0.0)
        wait = self.min_gap - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        self._last_request[domain] = time.time()

    def _is_transient(self, exc):
        """Transient = worth retrying (timeouts, 5xx, connection drops)."""
        if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
            return True
        resp = getattr(exc, "response", None)
        return bool(resp is not None and resp.status_code >= 500)

    # ── fetching ───────────────────────────────────────────────────────
    def fetch(self, url):
        """GET a page with UA rotation, rate limiting and backoff retries.

        Returns the HTML text, or None after all retries are exhausted.
        Subclasses (e.g. the Playwright spider) override this method.
        """
        for attempt in range(self.max_retries + 1):
            try:
                self._rate_limit(url)
                headers = {"User-Agent": self._pick_user_agent()}
                proxies = self._pick_proxy()
                resp = self.session.get(
                    url, headers=headers, proxies=proxies, timeout=self.timeout
                )
                resp.raise_for_status()
                self.stats.requests += 1
                return resp.text
            except Exception as exc:  # noqa: BLE001 - intentional: classify below
                transient = self._is_transient(exc)
                last_try = attempt == self.max_retries
                if not transient or last_try:
                    self.stats.errors += 1
                    print(f"  [error] {url}: {exc}")
                    return None
                wait = self.backoff_base ** attempt
                print(f"  [retry {attempt + 1}/{self.max_retries}] {url} "
                      f"in {wait:.0f}s ({exc})")
                time.sleep(wait)
        return None

    # ── crawl driver ───────────────────────────────────────────────────
    def parse_page(self, html, url):
        """Override in subclasses. Returns (items, next_urls)."""
        raise NotImplementedError

    def crawl(self, max_pages=None):
        """Breadth-first crawl of start_urls following pagination links.

        Yields item dicts. Updates run stats as it goes.
        """
        queue = list(self.start_urls)
        seen = set()
        pages = 0
        while queue and (max_pages is None or pages < max_pages):
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            pages += 1
            print(f"[{self.name}] page {pages}: {url}")
            html = self.fetch(url)
            if html is None:
                continue
            items, next_urls = self.parse_page(html, url)
            for item in items:
                self.stats.items += 1
                yield item
            for nxt in next_urls:
                if nxt not in seen:
                    queue.append(nxt)
