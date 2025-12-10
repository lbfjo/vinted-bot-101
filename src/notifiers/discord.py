import json
import logging
from typing import Optional

import requests

from src.fetcher.vinted import Listing
from src.notifiers.base import RuleContext

logger = logging.getLogger(__name__)


def send_discord_message(listing: Listing, context: RuleContext, webhook_url: str) -> None:
    if not webhook_url:
        logger.warning("Discord webhook URL not provided; skipping notification")
        return

    payload = {
        "content": f"New listing for {context.rule_name} ({context.locale}): {listing.title} - {listing.price} {listing.currency}",
        "embeds": [
            {
                "title": listing.title,
                "url": listing.url,
                "description": f"Price: {listing.price} {listing.currency}\nSize: {listing.size or 'n/a'}",
                "thumbnail": {"url": listing.thumbnail} if listing.thumbnail else None,
            }
        ],
    }

    response = requests.post(webhook_url, data=json.dumps(payload), headers={"Content-Type": "application/json"})
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to send Discord notification: %s", exc)


def notify(listing: Listing, context: RuleContext, webhook_url: Optional[str]) -> None:
    if webhook_url:
        send_discord_message(listing, context, webhook_url)
