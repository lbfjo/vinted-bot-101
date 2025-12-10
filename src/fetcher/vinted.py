from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Iterable, List, Optional
from urllib.parse import urlencode

import requests
from requests.exceptions import JSONDecodeError

logger = logging.getLogger(__name__)

# Vinted API endpoints by locale
VINTED_DOMAINS = {
    "fr": "www.vinted.fr",
    "de": "www.vinted.de",
    "es": "www.vinted.es",
    "it": "www.vinted.it",
    "nl": "www.vinted.nl",
    "be": "www.vinted.be",
    "at": "www.vinted.at",
    "pl": "www.vinted.pl",
    "cz": "www.vinted.cz",
    "lt": "www.vinted.lt",
    "pt": "www.vinted.pt",
    "sk": "www.vinted.sk",
    "uk": "www.vinted.co.uk",
    "en": "www.vinted.com",
    "us": "www.vinted.com",
}

# Rate limiting configuration
MIN_REQUEST_INTERVAL = 2.0  # seconds between requests
MAX_REQUEST_INTERVAL = 5.0  # random jitter range
MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0


@dataclass
class Listing:
    id: str
    title: str
    price: float
    currency: str
    size: str | None
    url: str
    thumbnail: str | None = None
    seller_rating: float | None = None
    seller_id: str | None = None
    brand: str | None = None
    condition: str | None = None


@dataclass
class RateLimiter:
    """Simple rate limiter to respect Vinted's rate limits."""

    last_request_time: float = 0.0

    def wait(self) -> None:
        """Wait appropriate time before next request."""
        now = time.time()
        elapsed = now - self.last_request_time
        min_wait = MIN_REQUEST_INTERVAL + random.uniform(0, MAX_REQUEST_INTERVAL - MIN_REQUEST_INTERVAL)

        if elapsed < min_wait:
            sleep_time = min_wait - elapsed
            logger.debug("Rate limiting: sleeping for %.2f seconds", sleep_time)
            time.sleep(sleep_time)

        self.last_request_time = time.time()


# Global rate limiter instance
_rate_limiter = RateLimiter()


def get_vinted_domain(locale: str) -> str:
    """Get the Vinted domain for a given locale."""
    return VINTED_DOMAINS.get(locale, VINTED_DOMAINS["en"])


def build_search_url(keyword: str, locale: str = "en") -> str:
    """Build a user-facing search URL for Vinted."""
    params = {
        "search_text": keyword,
        "order": "newest_first",
    }
    query = urlencode(params)
    domain = get_vinted_domain(locale)
    return f"https://{domain}/catalog?{query}"


def _get_session(locale: str) -> requests.Session:
    """Create a session with appropriate headers for Vinted API."""
    session = requests.Session()
    domain = get_vinted_domain(locale)

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        # Avoid advertising brotli (br) support because requests does not decode it
        # without optional dependencies, which leads to binary gibberish and JSON
        # decode errors. Gzip/deflate are decoded by default.
        "Accept-Encoding": "gzip, deflate",
        "Referer": f"https://{domain}/",
        "Origin": f"https://{domain}",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    })

    return session


def _fetch_oauth_token(session: requests.Session, locale: str) -> Optional[str]:
    """Fetch OAuth token from Vinted by visiting the main page."""
    domain = get_vinted_domain(locale)

    try:
        # First visit the main page to get cookies
        _rate_limiter.wait()
        response = session.get(f"https://{domain}", timeout=30)
        response.raise_for_status()

        # The access token is typically set as a cookie
        if "access_token" in session.cookies:
            return session.cookies["access_token"]

        # Some locales use _vinted_fr_session or similar
        for cookie_name in session.cookies.keys():
            if "session" in cookie_name.lower():
                logger.debug("Found session cookie: %s", cookie_name)

        return None
    except requests.RequestException as e:
        logger.warning("Failed to fetch OAuth token: %s", e)
        return None


def _parse_listing(item: dict, locale: str) -> Optional[Listing]:
    """Parse a listing item from Vinted API response."""
    try:
        item_id = str(item.get("id", ""))
        if not item_id:
            return None

        domain = get_vinted_domain(locale)

        # Extract price info
        price_data = item.get("price") or item.get("total_item_price") or {}
        if isinstance(price_data, dict):
            price = float(price_data.get("amount", 0))
            currency = price_data.get("currency_code", "EUR")
        else:
            price = float(price_data) if price_data else 0.0
            currency = "EUR"

        # Extract user/seller info
        user = item.get("user") or {}
        seller_rating = None
        seller_id = None
        if user:
            seller_id = str(user.get("id", ""))
            feedback = user.get("feedback_reputation")
            if feedback is not None:
                seller_rating = float(feedback)

        # Extract photo
        photo = item.get("photo") or {}
        thumbnail = photo.get("url") or photo.get("full_size_url")

        # Build listing URL
        url = item.get("url") or f"https://{domain}/items/{item_id}"
        if not url.startswith("http"):
            url = f"https://{domain}{url}"

        return Listing(
            id=item_id,
            title=item.get("title", "Unknown"),
            price=price,
            currency=currency,
            size=item.get("size_title") or item.get("size"),
            url=url,
            thumbnail=thumbnail,
            seller_rating=seller_rating,
            seller_id=seller_id,
            brand=item.get("brand_title") or (item.get("brand") or {}).get("title"),
            condition=item.get("status"),
        )
    except (ValueError, KeyError, TypeError) as e:
        logger.debug("Failed to parse listing: %s", e)
        return None


def fetch_new_listings(
    keywords: Iterable[str],
    locale: str = "en",
    price_max: Optional[float] = None,
    per_page: int = 20,
) -> List[Listing]:
    """Fetch new listings from Vinted for the provided keywords.

    Args:
        keywords: List of search terms to combine
        locale: Vinted locale/country code
        price_max: Optional maximum price filter
        per_page: Number of results per page (max 96)

    Returns:
        List of Listing objects sorted by newest first
    """
    domain = get_vinted_domain(locale)
    search_text = " ".join(keywords)

    session = _get_session(locale)

    # Build API URL
    params = {
        "search_text": search_text,
        "order": "newest_first",
        "per_page": min(per_page, 96),
        "page": 1,
    }

    if price_max is not None:
        params["price_to"] = price_max

    api_url = f"https://{domain}/api/v2/catalog/items"

    listings: List[Listing] = []

    for attempt in range(MAX_RETRIES):
        try:
            _rate_limiter.wait()

            logger.debug("Fetching from %s with params %s (attempt %d)", api_url, params, attempt + 1)
            response = session.get(api_url, params=params, timeout=30)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning("Rate limited. Waiting %d seconds before retry.", retry_after)
                time.sleep(retry_after)
                continue

            # Handle unauthorized - try to refresh session
            if response.status_code in (401, 403):
                logger.debug("Auth error, refreshing session...")
                session = _get_session(locale)
                _fetch_oauth_token(session, locale)
                continue

            response.raise_for_status()

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                body_preview = response.text.replace("\n", " ")[:200]
                content_type = response.headers.get("Content-Type", "unknown")
                lower_preview = body_preview.lower()
                block_hint = None

                if "cloudflare" in lower_preview or "attention required" in lower_preview:
                    block_hint = "Response looks like Cloudflare bot protection; the IP may be blocked."
                elif "captcha" in lower_preview:
                    block_hint = "Response contains a captcha page; Vinted may be challenging automated traffic."

                logger.error(
                    "Failed to decode JSON response (status %s, content-type %s): %s. Body preview: %s%s",
                    response.status_code,
                    content_type,
                    e,
                    body_preview,
                    f" Hint: {block_hint}" if block_hint else "",
                )

                if attempt < MAX_RETRIES - 1:
                    time.sleep(BACKOFF_FACTOR ** attempt)
                    continue
                break
            items = data.get("items", [])

            if not items:
                logger.debug("No items found in response")
                break

            for item in items:
                listing = _parse_listing(item, locale)
                if listing:
                    listings.append(listing)

            logger.info("Fetched %d listings for '%s' (%s)", len(listings), search_text, locale)
            break

        except requests.Timeout:
            logger.warning("Request timed out (attempt %d/%d)", attempt + 1, MAX_RETRIES)
            if attempt < MAX_RETRIES - 1:
                time.sleep(BACKOFF_FACTOR ** attempt)
        except requests.RequestException as e:
            logger.error("Request failed: %s (attempt %d/%d)", e, attempt + 1, MAX_RETRIES)
            if attempt < MAX_RETRIES - 1:
                time.sleep(BACKOFF_FACTOR ** attempt)
        except (ValueError, KeyError) as e:
            logger.error("Failed to parse response: %s", e)
            break

    return listings
