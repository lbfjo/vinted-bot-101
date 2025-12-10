import logging
from pathlib import Path

from src.config import AppConfig, load_config
from src.fetcher.vinted import build_search_url, fetch_new_listings
from src.notifiers import discord, slack
from src.notifiers.base import RuleContext

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def notify_for_search(config: AppConfig) -> None:
    for search in config.searches:
        logger.info("Running search '%s' across locales %s", search.name, ",".join(search.locales))
        for locale in search.locales:
            listings = fetch_new_listings(search.keywords, locale)
            if not listings:
                logger.info("No new listings for %s (%s)", search.name, locale)
                continue

            context = RuleContext(rule_name=search.name, locale=locale)
            for listing in listings:
                webhook = search.webhook or config.slack_webhook_url or config.discord_webhook_url
                if config.slack_webhook_url:
                    slack.notify(listing, context, config.slack_webhook_url)
                if config.discord_webhook_url:
                    discord.notify(listing, context, config.discord_webhook_url)
                if webhook is None:
                    logger.warning("No webhook configured for search %s", search.name)


def main(config_path: str | Path = "config/searches.yaml") -> None:
    config = load_config(config_path)
    if not config.searches:
        logger.warning("No searches configured. Add entries to %s", config_path)
        return

    for search in config.searches:
        logger.info("Preview search URL for '%s': %s", search.name, build_search_url(",".join(search.keywords)))

    notify_for_search(config)


if __name__ == "__main__":
    main()
