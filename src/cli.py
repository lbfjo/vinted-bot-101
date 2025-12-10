from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from src.config import AppConfig, SearchConfig, load_config
from src.fetcher.vinted import Listing, build_search_url, fetch_new_listings
from src.filters import filter_listings
from src.metrics import RunMetrics, SearchMetrics
from src.notifiers import discord, slack
from src.notifiers.base import RuleContext
from src.state import StateManager, get_state_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def process_search(
    search: SearchConfig,
    config: AppConfig,
    state_manager: StateManager,
    run_metrics: RunMetrics,
) -> None:
    """Process a single search configuration."""
    if not search.enabled:
        logger.info("Search '%s' is disabled, skipping", search.name)
        return

    logger.info("Running search '%s' across locales: %s", search.name, ", ".join(search.locales))

    for locale in search.locales:
        metrics = SearchMetrics(search_name=search.name, locale=locale)

        # Fetch listings from Vinted
        try:
            listings = fetch_new_listings(
                search.keywords,
                locale,
                price_max=search.price_max,
            )
            metrics.found = len(listings)
        except Exception as e:
            logger.error("Failed to fetch listings for %s (%s): %s", search.name, locale, e)
            metrics.errors += 1
            run_metrics.add_search_metrics(metrics)
            continue

        if not listings:
            logger.info("No listings found for %s (%s)", search.name, locale)
            run_metrics.add_search_metrics(metrics)
            continue

        # Filter out already-seen listings
        new_listings: List[Listing] = []
        for listing in listings:
            if state_manager.is_seen(search.name, listing.id):
                metrics.skipped_duplicate += 1
            else:
                new_listings.append(listing)

        metrics.new = len(new_listings)

        if not new_listings:
            logger.info("No new listings for %s (%s) (all %d already seen)", search.name, locale, metrics.found)
            run_metrics.add_search_metrics(metrics)
            continue

        # Apply filters (price, keywords, seller rating)
        passed_listings, skipped = filter_listings(new_listings, search)
        metrics.filtered_out = len(skipped)

        if not passed_listings:
            logger.info(
                "No listings passed filters for %s (%s) (%d filtered out)",
                search.name,
                locale,
                metrics.filtered_out,
            )
            # Mark all as seen even if filtered out
            for listing in new_listings:
                state_manager.mark_seen(search.name, listing.id)
            run_metrics.add_search_metrics(metrics)
            continue

        # Check cooldown
        cooldown = search.cooldown_minutes or config.default_cooldown_minutes
        if not state_manager.can_notify(search.name, cooldown):
            remaining = state_manager.get_time_until_notify(search.name, cooldown)
            logger.info(
                "Cooldown active for %s (%d seconds remaining), skipping %d notifications",
                search.name,
                remaining or 0,
                len(passed_listings),
            )
            metrics.skipped_cooldown = len(passed_listings)
            # Still mark as seen
            for listing in passed_listings:
                state_manager.mark_seen(search.name, listing.id)
            run_metrics.add_search_metrics(metrics)
            continue

        # Send notifications
        context = RuleContext(rule_name=search.name, locale=locale)

        # Determine webhooks
        slack_webhook = search.webhook or config.slack_webhook_url
        discord_webhook = config.discord_webhook_url

        # Limit to max batch size
        listings_to_notify = passed_listings[: config.max_batch_size]

        if config.batch_notifications and len(listings_to_notify) > 1:
            # Send batch notification
            notified = _send_batch_notifications(
                listings_to_notify, context, slack_webhook, discord_webhook
            )
            if notified:
                metrics.notified = len(listings_to_notify)
                state_manager.mark_notified(search.name)
        else:
            # Send individual notifications
            for listing in listings_to_notify:
                notified = _send_notifications(listing, context, slack_webhook, discord_webhook)
                if notified:
                    metrics.notified += 1

            if metrics.notified > 0:
                state_manager.mark_notified(search.name)

        # Mark all passed listings as seen
        for listing in passed_listings:
            state_manager.mark_seen(search.name, listing.id)

        metrics.log_summary()
        run_metrics.add_search_metrics(metrics)


def _send_notifications(
    listing: Listing,
    context: RuleContext,
    slack_webhook: str | None,
    discord_webhook: str | None,
) -> bool:
    """Send notifications for a single listing.

    Returns True if at least one notification was sent successfully.
    """
    sent = False

    if slack_webhook:
        if slack.notify(listing, context, slack_webhook):
            sent = True

    if discord_webhook:
        if discord.notify(listing, context, discord_webhook):
            sent = True

    if not slack_webhook and not discord_webhook:
        logger.warning("No webhook configured for %s", context.rule_name)

    return sent


def _send_batch_notifications(
    listings: List[Listing],
    context: RuleContext,
    slack_webhook: str | None,
    discord_webhook: str | None,
) -> bool:
    """Send batch notifications for multiple listings.

    Returns True if at least one notification was sent successfully.
    """
    sent = False

    if slack_webhook:
        if slack.notify_batch(listings, context, slack_webhook):
            sent = True

    if discord_webhook:
        if discord.notify_batch(listings, context, discord_webhook):
            sent = True

    if not slack_webhook and not discord_webhook:
        logger.warning("No webhook configured for %s", context.rule_name)

    return sent


def run_bot(config: AppConfig) -> RunMetrics:
    """Run the bot with the given configuration.

    Returns metrics from the run.
    """
    state_manager = get_state_manager(config.state_file)
    run_metrics = RunMetrics()

    # Preview search URLs
    logger.info("=" * 60)
    logger.info("VINTED BOT STARTING")
    logger.info("=" * 60)
    for search in config.searches:
        if search.enabled:
            for locale in search.locales:
                url = build_search_url(" ".join(search.keywords), locale)
                logger.info("Search '%s' (%s): %s", search.name, locale, url)
    logger.info("=" * 60)

    # Process each search
    for search in config.searches:
        try:
            process_search(search, config, state_manager, run_metrics)
        except Exception as e:
            logger.error("Error processing search '%s': %s", search.name, e)

    # Save state
    state_manager.save()

    # Cleanup old IDs
    state_manager.cleanup(config.max_seen_ids_per_search)
    state_manager.save()

    # Log run summary
    run_metrics.log_summary()

    return run_metrics


def main(config_path: str | Path = "config/searches.yaml") -> int:
    """Main entry point.

    Returns 0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        description="Vinted Bot - Monitor Vinted for new listings",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=str(config_path),
        help="Path to configuration file (default: config/searches.yaml)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch listings but don't send notifications",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        logger.error("Configuration file not found: %s", e)
        return 1
    except Exception as e:
        logger.error("Failed to load configuration: %s", e)
        return 1

    if not config.searches:
        logger.warning("No searches configured. Add entries to %s", args.config)
        return 0

    # Validate webhooks
    if not config.slack_webhook_url and not config.discord_webhook_url:
        logger.warning("No webhooks configured. Notifications will not be sent.")

    if args.dry_run:
        logger.info("DRY RUN MODE - No notifications will be sent")
        # Clear webhooks for dry run
        config.slack_webhook_url = None
        config.discord_webhook_url = None

    try:
        metrics = run_bot(config)
        return 0 if metrics.total_errors == 0 else 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
