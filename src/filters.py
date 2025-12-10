"""Listing filters for applying search rules."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

from src.config import SearchConfig
from src.fetcher.vinted import Listing

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Result of filtering a listing."""

    passed: bool
    reason: Optional[str] = None


def matches_keywords(text: str, keywords: List[str], case_insensitive: bool = True) -> bool:
    """Check if text contains any of the keywords."""
    if not keywords:
        return False

    if case_insensitive:
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in keywords)
    return any(kw in text for kw in keywords)


def filter_by_price(listing: Listing, price_min: Optional[float], price_max: Optional[float]) -> FilterResult:
    """Filter listing by price range."""
    if price_min is not None and listing.price < price_min:
        return FilterResult(False, f"Price {listing.price} below minimum {price_min}")

    if price_max is not None and listing.price > price_max:
        return FilterResult(False, f"Price {listing.price} above maximum {price_max}")

    return FilterResult(True)


def filter_by_keywords(
    listing: Listing,
    include_keywords: List[str],
    exclude_keywords: List[str],
) -> FilterResult:
    """Filter listing by include/exclude keyword lists."""
    text = f"{listing.title} {listing.brand or ''}"

    # Check exclude keywords first
    if exclude_keywords and matches_keywords(text, exclude_keywords):
        matched = [kw for kw in exclude_keywords if kw.lower() in text.lower()]
        return FilterResult(False, f"Contains excluded keyword(s): {', '.join(matched)}")

    # Check include keywords (if specified, at least one must match)
    if include_keywords and not matches_keywords(text, include_keywords):
        return FilterResult(False, f"Missing required keyword(s): {', '.join(include_keywords)}")

    return FilterResult(True)


def filter_by_seller_rating(
    listing: Listing,
    min_rating: Optional[float],
    min_reviews: Optional[int] = None,
) -> FilterResult:
    """Filter listing by seller rating threshold."""
    if min_rating is not None:
        if listing.seller_rating is None:
            return FilterResult(False, "Seller rating not available")

        if listing.seller_rating < min_rating:
            return FilterResult(
                False,
                f"Seller rating {listing.seller_rating:.1f} below minimum {min_rating:.1f}",
            )

    return FilterResult(True)


def apply_filters(listing: Listing, search: SearchConfig) -> FilterResult:
    """Apply all filters from a search configuration to a listing.

    Returns FilterResult with passed=True if listing passes all filters,
    or passed=False with the reason for the first filter that failed.
    """
    # Price filter
    result = filter_by_price(listing, search.price_min, search.price_max)
    if not result.passed:
        return result

    # Keyword include/exclude filter
    result = filter_by_keywords(listing, search.include_keywords, search.exclude_keywords)
    if not result.passed:
        return result

    # Seller rating filter
    result = filter_by_seller_rating(listing, search.min_seller_rating, search.min_seller_reviews)
    if not result.passed:
        return result

    return FilterResult(True)


def filter_listings(listings: List[Listing], search: SearchConfig) -> tuple[List[Listing], List[tuple[Listing, str]]]:
    """Filter a list of listings based on search configuration.

    Returns:
        Tuple of (passed_listings, skipped_listings_with_reasons)
    """
    passed: List[Listing] = []
    skipped: List[tuple[Listing, str]] = []

    for listing in listings:
        result = apply_filters(listing, search)
        if result.passed:
            passed.append(listing)
        else:
            skipped.append((listing, result.reason or "Unknown"))
            logger.debug(
                "Filtered out '%s' (%.2f %s): %s",
                listing.title,
                listing.price,
                listing.currency,
                result.reason,
            )

    return passed, skipped
