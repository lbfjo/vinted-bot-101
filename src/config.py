import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml


@dataclass
class SearchConfig:
    name: str
    keywords: List[str]
    price_max: float | None = None
    locales: List[str] = field(default_factory=lambda: ["en"])
    webhook: str | None = None


@dataclass
class AppConfig:
    searches: List[SearchConfig]
    slack_webhook_url: str | None = None
    discord_webhook_url: str | None = None
    poll_interval_seconds: int = 300


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


def load_config(path: str | Path = "config/searches.yaml") -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw = _load_yaml(config_path)

    slack_webhook = os.getenv("SLACK_WEBHOOK_URL", raw.get("slack_webhook_url"))
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL", raw.get("discord_webhook_url"))

    searches: List[SearchConfig] = []
    for search in raw.get("searches", []):
        searches.append(
            SearchConfig(
                name=search.get("name", "default"),
                keywords=search.get("keywords", []),
                price_max=search.get("price_max"),
                locales=search.get("locales", ["en"]),
                webhook=search.get("webhook"),
            )
        )

    return AppConfig(
        searches=searches,
        slack_webhook_url=slack_webhook,
        discord_webhook_url=discord_webhook,
        poll_interval_seconds=raw.get("poll_interval_seconds", 300),
    )
