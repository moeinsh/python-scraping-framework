"""Demo spider 1: book catalog at books.toscrape.com.

Extracts title, price and availability from listing pages, then follows
each product's detail page to pick up its category (breadcrumb).
"""
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..core import BaseSpider


class BooksSpider(BaseSpider):
    name = "books"
    start_urls = ["http://books.toscrape.com/"]
    fields = ["title", "price", "availability", "category", "product_url"]

    def parse_page(self, html, url):
        soup = BeautifulSoup(html, "html.parser")
        items = []
        detail_urls = []

        for pod in soup.select("article.product_pod"):
            link = pod.select_one("h3 a")
            title = link.get("title", "").strip()
            product_url = urljoin(url, link.get("href", ""))
            price = pod.select_one("p.price_color").get_text(strip=True)
            avail = pod.select_one("p.instock").get_text(strip=True)
            items.append({
                "title": title,
                "price": price,
                "availability": avail,
                "category": "",          # filled in from the detail page
                "product_url": product_url,
            })
            detail_urls.append((product_url, len(items) - 1))

        # Enrich with category from each product detail page.
        for product_url, idx in detail_urls:
            detail_html = self.fetch(product_url)
            if detail_html:
                crumbs = BeautifulSoup(detail_html, "html.parser").select(
                    "ul.breadcrumb li a"
                )
                if crumbs:
                    items[idx]["category"] = crumbs[-1].get_text(strip=True)

        next_urls = []
        nxt = soup.select_one("li.next a")
        if nxt and nxt.get("href"):
            next_urls.append(urljoin(url, nxt["href"]))
        return items, next_urls
