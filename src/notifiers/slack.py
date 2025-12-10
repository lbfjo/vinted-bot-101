import json
import logging
from typing import Optional

import requests

from src.fetcher.vinted import Listing
from src.notifiers.base import RuleContext

logger = logging.getLogger(__name__)


def send_slack_message(listing: Listing, context: RuleContext, webhook_url: str) -> None:
    if not webhook_url:
        logger.warning("Slack webhook URL not provided; skipping notification")
        return

    payload = {
        "text": f"New listing for {context.rule_name} ({context.locale}): {listing.title} - {listing.price} {listing.currency}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{listing.title}*\nPrice: {listing.price} {listing.currency}\nSize: {listing.size or 'n/a'}\n<{listing.url}|View on Vinted>",
                },
            }
        ],
    }

    if listing.thumbnail:
        payload["blocks"].append(
            {
                "type": "image",
                "image_url": listing.thumbnail,
                "alt_text": listing.title,
            }
        )

    response = requests.post(webhook_url, data=json.dumps(payload), headers={"Content-Type": "application/json"})
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to send Slack notification: %s", exc)


def notify(listing: Listing, context: RuleContext, webhook_url: Optional[str]) -> None:
    if webhook_url:
        send_slack_message(listing, context, webhook_url)
