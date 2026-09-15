"""Production-grade web scraping framework (sample project)."""
from .core import BaseSpider, RunStats
from .pipelines import CSVPipeline, SQLitePipeline
from .config import load_config

__all__ = ["BaseSpider", "RunStats", "CSVPipeline", "SQLitePipeline", "load_config"]
