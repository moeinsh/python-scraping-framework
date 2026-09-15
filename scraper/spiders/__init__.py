"""Spider registry.

The Playwright-based spider is registered only when Playwright is
installed, so the rest of the framework works without that optional
dependency.
"""
from .books import BooksSpider
from .quotes import QuotesSpider

SPIDERS = {
    BooksSpider.name: BooksSpider,
    QuotesSpider.name: QuotesSpider,
}

try:
    from .js_quotes import JSQuotesSpider
    SPIDERS[JSQuotesSpider.name] = JSQuotesSpider
except ImportError:  # Playwright not installed -> JS spider unavailable
    pass
