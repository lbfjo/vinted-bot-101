"""Metrics tracking for the Vinted bot."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class SearchMetrics:
    """Metrics for a single search execution."""

    search_name: str
    locale: str
    found: int = 0
    new: int = 0
    filtered_out: int = 0
    notified: int = 0
    skipped_cooldown: int = 0
    skipped_duplicate: int = 0
    errors: int = 0

    def log_summary(self) -> None:
        """Log a summary of metrics for this search."""
        logger.info(
            "[%s/%s] Found: %d, New: %d, Filtered: %d, Notified: %d, Skipped (cooldown): %d, Skipped (dup): %d",
            self.search_name,
            self.locale,
            self.found,
            self.new,
            self.filtered_out,
            self.notified,
            self.skipped_cooldown,
            self.skipped_duplicate,
        )


@dataclass
class RunMetrics:
    """Aggregated metrics for a complete bot run."""

    search_metrics: List[SearchMetrics] = field(default_factory=list)

    @property
    def total_found(self) -> int:
        return sum(m.found for m in self.search_metrics)

    @property
    def total_new(self) -> int:
        return sum(m.new for m in self.search_metrics)

    @property
    def total_filtered(self) -> int:
        return sum(m.filtered_out for m in self.search_metrics)

    @property
    def total_notified(self) -> int:
        return sum(m.notified for m in self.search_metrics)

    @property
    def total_skipped_cooldown(self) -> int:
        return sum(m.skipped_cooldown for m in self.search_metrics)

    @property
    def total_skipped_duplicate(self) -> int:
        return sum(m.skipped_duplicate for m in self.search_metrics)

    @property
    def total_errors(self) -> int:
        return sum(m.errors for m in self.search_metrics)

    def add_search_metrics(self, metrics: SearchMetrics) -> None:
        """Add metrics from a search execution."""
        self.search_metrics.append(metrics)

    def log_summary(self) -> None:
        """Log a summary of the entire run."""
        logger.info("=" * 60)
        logger.info("RUN SUMMARY")
        logger.info("=" * 60)
        logger.info("Searches executed: %d", len(self.search_metrics))
        logger.info("Total listings found: %d", self.total_found)
        logger.info("New listings: %d", self.total_new)
        logger.info("Filtered out: %d", self.total_filtered)
        logger.info("Notifications sent: %d", self.total_notified)
        logger.info("Skipped (cooldown): %d", self.total_skipped_cooldown)
        logger.info("Skipped (duplicate): %d", self.total_skipped_duplicate)
        if self.total_errors > 0:
            logger.warning("Errors: %d", self.total_errors)
        logger.info("=" * 60)

    def to_dict(self) -> dict:
        """Convert metrics to dictionary for JSON output."""
        return {
            "searches_executed": len(self.search_metrics),
            "total_found": self.total_found,
            "total_new": self.total_new,
            "total_filtered": self.total_filtered,
            "total_notified": self.total_notified,
            "total_skipped_cooldown": self.total_skipped_cooldown,
            "total_skipped_duplicate": self.total_skipped_duplicate,
            "total_errors": self.total_errors,
            "searches": [
                {
                    "name": m.search_name,
                    "locale": m.locale,
                    "found": m.found,
                    "new": m.new,
                    "filtered_out": m.filtered_out,
                    "notified": m.notified,
                    "skipped_cooldown": m.skipped_cooldown,
                    "skipped_duplicate": m.skipped_duplicate,
                    "errors": m.errors,
                }
                for m in self.search_metrics
            ],
        }
