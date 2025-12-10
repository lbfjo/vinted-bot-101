import json
import logging
from typing import List, Optional

import requests

from src.fetcher.vinted import Listing
from src.notifiers.base import RuleContext

logger = logging.getLogger(__name__)


def _build_listing_block(listing: Listing) -> dict:
    """Build a Slack block for a single listing."""
    # Build description with available info
    details = [f"*Price:* {listing.price:.2f} {listing.currency}"]

    if listing.size:
        details.append(f"*Size:* {listing.size}")

    if listing.brand:
        details.append(f"*Brand:* {listing.brand}")

    if listing.condition:
        details.append(f"*Condition:* {listing.condition}")

    if listing.seller_rating is not None:
        details.append(f"*Seller Rating:* {listing.seller_rating:.1f}⭐")

    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*<{listing.url}|{listing.title}>*\n" + " | ".join(details),
        },
        "accessory": {
            "type": "image",
            "image_url": listing.thumbnail or "https://via.placeholder.com/64",
            "alt_text": listing.title,
        } if listing.thumbnail else None,
    }


def send_slack_message(listing: Listing, context: RuleContext, webhook_url: str) -> bool:
    """Send a single listing notification to Slack.

    Returns True if successful, False otherwise.
    """
    if not webhook_url:
        logger.warning("Slack webhook URL not provided; skipping notification")
        return False

    block = _build_listing_block(listing)
    # Remove None accessory if no thumbnail
    if block.get("accessory") is None:
        del block["accessory"]

    payload = {
        "text": f"New listing for {context.rule_name} ({context.locale}): {listing.title} - {listing.price:.2f} {listing.currency}",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔔 New: {context.rule_name} ({context.locale})",
                    "emoji": True,
                },
            },
            block,
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"<{listing.url}|View on Vinted> • Listing ID: {listing.id}",
                    }
                ],
            },
            {"type": "divider"},
        ],
    }

    return _send_payload(webhook_url, payload)


def send_batch_notification(
    listings: List[Listing],
    context: RuleContext,
    webhook_url: str,
) -> bool:
    """Send a batch notification with multiple listings to Slack.

    Returns True if successful, False otherwise.
    """
    if not webhook_url:
        logger.warning("Slack webhook URL not provided; skipping notification")
        return False

    if not listings:
        return True

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔔 {len(listings)} New Listings: {context.rule_name} ({context.locale})",
                "emoji": True,
            },
        },
    ]

    for listing in listings:
        block = _build_listing_block(listing)
        if block.get("accessory") is None:
            del block["accessory"]
        blocks.append(block)
        blocks.append({"type": "divider"})

    # Summary at the end
    total_value = sum(l.price for l in listings)
    avg_price = total_value / len(listings) if listings else 0
    currency = listings[0].currency if listings else "EUR"

    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"📊 Total: {len(listings)} items | Avg price: {avg_price:.2f} {currency}",
            }
        ],
    })

    payload = {
        "text": f"{len(listings)} new listings for {context.rule_name} ({context.locale})",
        "blocks": blocks,
    }

    return _send_payload(webhook_url, payload)


def _send_payload(webhook_url: str, payload: dict) -> bool:
    """Send a payload to Slack webhook.

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
        logger.error("Failed to send Slack notification: %s", exc)
        return False


def notify(listing: Listing, context: RuleContext, webhook_url: Optional[str]) -> bool:
    """Send a single listing notification.

    Returns True if successful, False otherwise.
    """
    if webhook_url:
        return send_slack_message(listing, context, webhook_url)
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
