# Scraping Framework (Python) — sample project

A small, production-style web scraping framework: spiders declare *what* to
extract, the framework handles *how* — polite fetching, retries, proxies,
and dual output. Three demo spiders ship with it, scraping real pages from
the canonical scraping-practice sites `books.toscrape.com` and
`quotes.toscrape.com`.

Demo results (real runs, 2026-09-15):

| spider | target | items |
|---|---|---|
| `books` | books.toscrape.com catalog (2 pages) — title, price, availability, category via detail pages | 40 books |
| `quotes` | quotes.toscrape.com — quote text, author, tags, all 10 pages | 100 quotes |
| `js_quotes` | quotes.toscrape.com/js/ — same data, JavaScript-rendered, via Playwright | 100 quotes* |

\* `js_quotes` parsing, pagination and both pipelines were verified end-to-end
against the live site (100 items, 10 pages, 0 errors). The Playwright
rendering step itself needs Chromium on the run machine
(`python -m playwright install chromium`); in sandboxed/CI environments
without browser egress it cannot execute.

Every run writes **both** `output/<spider>.csv` and `output/<spider>.db`
(SQLite), plus a run report (`items scraped, errors, duration`) to `runs/`.

## Architecture

```
                    ┌──────────────┐
                    │ run_spider.py│  CLI: picks spider, wires pipelines
                    └──────┬───────┘
                           │
              ┌────────────▼────────────┐
              │   BaseSpider (core.py)  │
              │  ┌───────────────────┐  │
              │  │ fetch()           │◄─┼── rotating User-Agents
              │  │  ├ rate limiter   │◄─┼── per-domain minimum gap
              │  │  ├ retry/backoff  │◄─┼── 2s → 4s → 8s on transient errors
              │  │  └ proxy rotation │◄─┼── optional, off by default
              │  └───────────────────┘  │
              │  crawl(): queue → fetch → parse_page → items
              │  RunStats: requests / items / errors / duration → runs/*.json
              └────────────┬────────────┘
                           │  items (dicts)
              ┌────────────▼────────────┐
              │  pipelines.py           │
              │  CSVPipeline ──► output/<spider>.csv
              │  SQLitePipeline ─► output/<spider>.db (table: items)
              └─────────────────────────┘

  spiders/books.py      listing pages + detail-page enrichment (category)
  spiders/quotes.py     paginated listing (plain HTTP)
  spiders/js_quotes.py  overrides fetch() → headless Chromium (Playwright)
```

`config.yaml` controls user-agents, rate limit, retry policy, proxies,
Playwright options, and output locations — no code changes needed to
retune a crawl.

## Run it

```bash
pip install -r requirements.txt
python -m playwright install chromium   # only needed for js_quotes
python run_spider.py quotes              # 100 quotes, ~15 s
python run_spider.py books --pages 2     # 40 books incl. detail pages
python run_spider.py js_quotes           # 100 quotes via headless Chromium
python run_spider.py all
```

Outputs land in `output/` (CSV + SQLite) and `runs/` (per-run JSON stats).

## Add a new spider in 3 steps

1. Create `scraper/spiders/myspider.py`:

```python
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from ..core import BaseSpider

class MySpider(BaseSpider):
    name = "myspider"
    start_urls = ["https://example.com/list"]
    fields = ["title", "price", "url"]

    def parse_page(self, html, url):
        soup = BeautifulSoup(html, "html.parser")
        items = [{"title": a.get_text(strip=True), ...}
                 for a in soup.select("...")]
        nxt = soup.select_one("a.next")
        next_urls = [urljoin(url, nxt["href"])] if nxt else []
        return items, next_urls
```

2. Register it in `scraper/spiders/__init__.py` (`SPIDERS[MySpider.name] = MySpider`).
3. Run it: `python run_spider.py myspider` — CSV, SQLite and run stats are automatic.

For JavaScript-rendered pages, subclass and override `fetch()` exactly like
`spiders/js_quotes.py` does (see its ~20 lines of Playwright code).

## Anti-blocking features

- **Rotating User-Agents** — a fresh browser identity on every request
  (`config.yaml: user_agents`)
- **Per-domain rate limiting** — configurable minimum gap between requests
  to the same host (default 1 s)
- **Retries with exponential backoff** — transient failures (timeouts,
  connection drops, HTTP 5xx) retried with 2 s → 4 s → 8 s waits;
  permanent failures (HTTP 4xx) fail fast and are logged
- **Proxy rotation** — list proxies in `config.yaml` and flip
  `proxies_enabled: true`; requests rotate through them. Off by default.
- **Polite defaults** — timeouts on every request, no concurrent hammering,
  demo spiders capped to a few pages

## Notes on scaling

This sample runs single-process and sequential by design (polite, easy to
debug). To scale it toward production workloads:

- **Queues** — replace the in-memory URL queue in `crawl()` with Redis/RQ
  or a database-backed frontier for pause/resume and multi-worker crawls
- **Concurrency** — run spiders in threads/async workers with a shared
  per-domain rate limiter (token bucket) instead of sleeps
- **Distributed runs** — one worker per domain shard, shared proxy pool,
  central dedup (seen-URL set in Redis), stats aggregated per run id
- **Robustness** — CAPTCHA/JS-wall handling, per-domain retry budgets,
  dead-letter queue for failed URLs, schema validation on items

## Scope and limitations (honest)

- Built and verified against `books.toscrape.com` / `quotes.toscrape.com`,
  which are practice sites that *welcome* scrapers. Real targets add
  login walls, aggressive bot detection, and legal/ToS constraints —
  always check a site's `robots.txt` and Terms of Service first.
- Proxy support is implemented and config-driven but was **not**
  live-tested (no proxy credentials in this demo) — `proxies_enabled`
  stays `false` by default.
- No CAPTCHA solving, no login/session management, no JavaScript
  interaction beyond page rendering (clicks, infinite scroll) — those
  are per-project extensions, not included here.
- This is a demonstration sample showing my scraping-framework workflow
  end to end. No client, no fake data — every row in `output/` came from
  a real run on 2026-09-15.

---

**Author:** Moein Shahidi — [@moeinsh](https://github.com/moeinsh)

© 2026 Moein Shahidi. Released under the MIT License.
