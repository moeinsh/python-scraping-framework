#!/usr/bin/env python3
"""CLI entry point: run one spider or all of them.

Usage:
    python run_spider.py books            # 2 catalog pages (demo default)
    python run_spider.py books --pages 5
    python run_spider.py quotes           # all 10 pages
    python run_spider.py js_quotes        # JS-rendered, via Playwright
    python run_spider.py all
"""
import argparse
import sys

from scraper import load_config, BaseSpider, CSVPipeline, SQLitePipeline
from scraper.spiders import SPIDERS

DEFAULT_PAGES = {"books": 2, "quotes": None, "js_quotes": None}


def run_one(spider_cls, config, max_pages):
    spider: BaseSpider = spider_cls(config)
    print(f"\n=== spider: {spider.name} ===")
    out_dir = config["output_dir"]
    csv_pipe = CSVPipeline(out_dir, spider.name, spider.fields)
    db_pipe = SQLitePipeline(out_dir, spider.name, spider.fields)
    try:
        for item in spider.crawl(max_pages=max_pages):
            csv_pipe.process_item(item)
            db_pipe.process_item(item)
    finally:
        if hasattr(spider, "close"):
            spider.close()
    csv_path, csv_n = csv_pipe.close()
    db_path, db_n = db_pipe.close()
    stats_path = spider.stats.save(config["runs_dir"])
    s = spider.stats.to_dict()
    print(f"  items: {s['items']}   requests: {s['requests']}   "
          f"errors: {s['errors']}   duration: {s['duration_seconds']}s")
    print(f"  CSV:   {csv_path} ({csv_n} rows)")
    print(f"  SQLite:{db_path} ({db_n} rows)")
    print(f"  stats: {stats_path}")
    return s


def main():
    ap = argparse.ArgumentParser(description="Run scraping-framework spiders")
    ap.add_argument("spider", choices=[*SPIDERS, "all"],
                    help="which spider to run")
    ap.add_argument("--pages", type=int, default=None,
                    help="max listing pages (overrides demo default)")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()

    config = load_config(args.config)
    names = list(SPIDERS) if args.spider == "all" else [args.spider]
    for name in names:
        pages = args.pages if args.pages is not None else DEFAULT_PAGES[name]
        run_one(SPIDERS[name], config, pages)
    print("\nDone.")


if __name__ == "__main__":
    sys.exit(main())
