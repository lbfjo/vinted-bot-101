from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


@dataclass
class SearchConfig:
    """Configuration for a single search rule."""

    name: str
    keywords: List[str]
    price_max: Optional[float] = None
    price_min: Optional[float] = None
    locales: List[str] = field(default_factory=lambda: ["en"])
    webhook: Optional[str] = None
    # Keyword filtering
    include_keywords: List[str] = field(default_factory=list)
    exclude_keywords: List[str] = field(default_factory=list)
    # Seller filtering
    min_seller_rating: Optional[float] = None
    min_seller_reviews: Optional[int] = None
    # Cooldown override (minutes)
    cooldown_minutes: Optional[int] = None
    # Enable/disable this search
    enabled: bool = True


@dataclass
class AppConfig:
    """Main application configuration."""

    searches: List[SearchConfig]
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    poll_interval_seconds: int = 300
    # Default cooldown in minutes (can be overridden per search)
    default_cooldown_minutes: int = 60
    # State file path
    state_file: str = "data/state.json"
    # Maximum IDs to keep per search (for cleanup)
    max_seen_ids_per_search: int = 1000
    # Batch notifications when multiple matches appear
    batch_notifications: bool = False
    # Maximum notifications per batch
    max_batch_size: int = 10


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
    state_file = os.getenv("STATE_FILE", raw.get("state_file", "data/state.json"))

    searches: List[SearchConfig] = []
    for search in raw.get("searches", []):
        searches.append(
            SearchConfig(
                name=search.get("name", "default"),
                keywords=search.get("keywords", []),
                price_max=search.get("price_max"),
                price_min=search.get("price_min"),
                locales=search.get("locales", ["en"]),
                webhook=search.get("webhook"),
                include_keywords=search.get("include_keywords", []),
                exclude_keywords=search.get("exclude_keywords", []),
                min_seller_rating=search.get("min_seller_rating"),
                min_seller_reviews=search.get("min_seller_reviews"),
                cooldown_minutes=search.get("cooldown_minutes"),
                enabled=search.get("enabled", True),
            )
        )

    return AppConfig(
        searches=searches,
        slack_webhook_url=slack_webhook,
        discord_webhook_url=discord_webhook,
        poll_interval_seconds=raw.get("poll_interval_seconds", 300),
        default_cooldown_minutes=raw.get("default_cooldown_minutes", 60),
        state_file=state_file,
        max_seen_ids_per_search=raw.get("max_seen_ids_per_search", 1000),
        batch_notifications=raw.get("batch_notifications", False),
        max_batch_size=raw.get("max_batch_size", 10),
    )
