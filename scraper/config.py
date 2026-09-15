"""Load framework configuration from config.yaml."""
import os
import yaml

DEFAULTS = {
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ],
    "rate_limit_seconds": 1.0,
    "max_retries": 3,
    "backoff_base": 2.0,
    "request_timeout": 20,
    "proxies_enabled": False,
    "proxies": [],
    "playwright_headless": True,
    "playwright_timeout_ms": 30000,
    "output_dir": "output",
    "runs_dir": "runs",
}


def load_config(path="config.yaml"):
    """Read YAML config, falling back to DEFAULTS for missing keys."""
    cfg = dict(DEFAULTS)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cfg.update(yaml.safe_load(f) or {})
    return cfg
