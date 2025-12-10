import json
import logging
from typing import List, Optional

import requests

from src.fetcher.vinted import Listing
from src.notifiers.base import RuleContext

logger = logging.getLogger(__name__)

# Discord embed color (green for new listings)
EMBED_COLOR = 0x00D166


def _build_embed(listing: Listing) -> dict:
    """Build a Discord embed for a single listing."""
    # Build description with available info
    description_parts = [f"**Price:** {listing.price:.2f} {listing.currency}"]

    if listing.size:
        description_parts.append(f"**Size:** {listing.size}")

    if listing.brand:
        description_parts.append(f"**Brand:** {listing.brand}")

    if listing.condition:
        description_parts.append(f"**Condition:** {listing.condition}")

    if listing.seller_rating is not None:
        description_parts.append(f"**Seller Rating:** {listing.seller_rating:.1f}⭐")

    embed = {
        "title": listing.title,
        "url": listing.url,
        "description": "\n".join(description_parts),
        "color": EMBED_COLOR,
        "footer": {"text": f"ID: {listing.id}"},
    }

    if listing.thumbnail:
        embed["thumbnail"] = {"url": listing.thumbnail}

    return embed


def send_discord_message(listing: Listing, context: RuleContext, webhook_url: str) -> bool:
    """Send a single listing notification to Discord.

    Returns True if successful, False otherwise.
    """
    if not webhook_url:
        logger.warning("Discord webhook URL not provided; skipping notification")
        return False

    embed = _build_embed(listing)

    payload = {
        "content": f"🔔 **New listing for {context.rule_name} ({context.locale})**",
        "embeds": [embed],
    }

    return _send_payload(webhook_url, payload)


def send_batch_notification(
    listings: List[Listing],
    context: RuleContext,
    webhook_url: str,
) -> bool:
    """Send a batch notification with multiple listings to Discord.

    Returns True if successful, False otherwise.
    """
    if not webhook_url:
        logger.warning("Discord webhook URL not provided; skipping notification")
        return False

    if not listings:
        return True

    # Discord allows max 10 embeds per message
    embeds = [_build_embed(listing) for listing in listings[:10]]

    # Summary embed
    total_value = sum(l.price for l in listings)
    avg_price = total_value / len(listings) if listings else 0
    currency = listings[0].currency if listings else "EUR"

    summary_embed = {
        "title": "📊 Batch Summary",
        "description": f"**Total items:** {len(listings)}\n**Average price:** {avg_price:.2f} {currency}",
        "color": 0x5865F2,  # Discord blurple
    }

    if len(listings) > 10:
        summary_embed["footer"] = {"text": f"Showing first 10 of {len(listings)} listings"}

    embeds.append(summary_embed)

    payload = {
        "content": f"🔔 **{len(listings)} new listings for {context.rule_name} ({context.locale})**",
        "embeds": embeds,
    }

    return _send_payload(webhook_url, payload)


def _send_payload(webhook_url: str, payload: dict) -> bool:
    """Send a payload to Discord webhook.

    Returns True if successful, False otherwise.
    """
    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.error("Failed to send Discord notification: %s", exc)
        return False


def notify(listing: Listing, context: RuleContext, webhook_url: Optional[str]) -> bool:
    """Send a single listing notification.

    Returns True if successful, False otherwise.
    """
    if webhook_url:
        return send_discord_message(listing, context, webhook_url)
    return False


def notify_batch(
    listings: List[Listing],
    context: RuleContext,
    webhook_url: Optional[str],
) -> bool:
    """Send a batch notification with multiple listings.

    Returns True if successful, False otherwise.
    """
    if webhook_url:
        return send_batch_notification(listings, context, webhook_url)
    return False
