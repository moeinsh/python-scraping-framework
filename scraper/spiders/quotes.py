"""Demo spider 2: quotes at quotes.toscrape.com (server-rendered, paginated)."""
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..core import BaseSpider


def parse_quotes(soup, url):
    """Shared quote extraction (also reused by the JS spider)."""
    items = []
    for block in soup.select("div.quote"):
        text = block.select_one("span.text").get_text(strip=True)
        author = block.select_one("small.author").get_text(strip=True)
        tags = [t.get_text(strip=True) for t in block.select("div.tags a.tag")]
        items.append({
            "text": text,
            "author": author,
            "tags": ", ".join(tags),
            "page_url": url,
        })
    return items


class QuotesSpider(BaseSpider):
    name = "quotes"
    start_urls = ["http://quotes.toscrape.com/"]
    fields = ["text", "author", "tags", "page_url"]

    def parse_page(self, html, url):
        soup = BeautifulSoup(html, "html.parser")
        items = parse_quotes(soup, url)
        next_urls = []
        nxt = soup.select_one("li.next a")
        if nxt and nxt.get("href"):
            next_urls.append(urljoin(url, nxt["href"]))
        return items, next_urls
