from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List
from urllib.parse import urlencode


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


def build_search_url(keyword: str, locale: str = "en") -> str:
    domain_by_locale = {
        "en": "com",
        "fr": "fr",
        "de": "de",
        "nl": "nl",
        "pl": "pl",
    }
    domain = domain_by_locale.get(locale, locale)

    params = {
        "search_text": keyword,
        "order": "newest_first",
    }
    query = urlencode(params)
    return f"https://www.vinted.{domain}/catalog?{query}"


def fetch_new_listings(keywords: Iterable[str], locale: str = "en") -> List[Listing]:
    """Placeholder fetcher that would query Vinted for the provided keywords.

    The current implementation returns an empty list and should be replaced with
    a real HTTP client that respects Vinted's rate limits and robots.txt.
    """
    _ = keywords  # avoid unused variable warning until implemented
    return []
