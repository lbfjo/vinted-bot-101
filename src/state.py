"""State management for duplicate suppression and cooldowns."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)

DEFAULT_STATE_FILE = "data/state.json"
DEFAULT_COOLDOWN_MINUTES = 60  # Default cooldown window


@dataclass
class SearchState:
    """State for a single search, tracking seen listings and last notification time."""

    seen_ids: Set[str] = field(default_factory=set)
    last_notification_time: Optional[str] = None  # ISO format timestamp

    def to_dict(self) -> dict:
        return {
            "seen_ids": list(self.seen_ids),
            "last_notification_time": self.last_notification_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SearchState":
        return cls(
            seen_ids=set(data.get("seen_ids", [])),
            last_notification_time=data.get("last_notification_time"),
        )


@dataclass
class AppState:
    """Application state for tracking seen listings across searches."""

    searches: Dict[str, SearchState] = field(default_factory=dict)
    version: int = 1

    def get_search_state(self, search_name: str) -> SearchState:
        """Get or create state for a search."""
        if search_name not in self.searches:
            self.searches[search_name] = SearchState()
        return self.searches[search_name]

    def is_seen(self, search_name: str, listing_id: str) -> bool:
        """Check if a listing has been seen for a search."""
        state = self.get_search_state(search_name)
        return listing_id in state.seen_ids

    def mark_seen(self, search_name: str, listing_id: str) -> None:
        """Mark a listing as seen for a search."""
        state = self.get_search_state(search_name)
        state.seen_ids.add(listing_id)

    def mark_notified(self, search_name: str) -> None:
        """Update the last notification time for a search."""
        state = self.get_search_state(search_name)
        state.last_notification_time = datetime.utcnow().isoformat()

    def can_notify(self, search_name: str, cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES) -> bool:
        """Check if enough time has passed since the last notification."""
        state = self.get_search_state(search_name)

        if state.last_notification_time is None:
            return True

        try:
            last_time = datetime.fromisoformat(state.last_notification_time)
            cooldown = timedelta(minutes=cooldown_minutes)
            return datetime.utcnow() - last_time >= cooldown
        except (ValueError, TypeError):
            return True

    def get_time_until_notify(self, search_name: str, cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES) -> Optional[int]:
        """Get seconds remaining until notification is allowed, or None if can notify now."""
        state = self.get_search_state(search_name)

        if state.last_notification_time is None:
            return None

        try:
            last_time = datetime.fromisoformat(state.last_notification_time)
            cooldown = timedelta(minutes=cooldown_minutes)
            remaining = (last_time + cooldown) - datetime.utcnow()
            if remaining.total_seconds() > 0:
                return int(remaining.total_seconds())
            return None
        except (ValueError, TypeError):
            return None

    def cleanup_old_ids(self, search_name: str, max_ids: int = 1000) -> int:
        """Clean up old listing IDs to prevent unbounded growth.

        Keeps the most recent max_ids entries.
        Returns the number of IDs removed.
        """
        state = self.get_search_state(search_name)
        if len(state.seen_ids) <= max_ids:
            return 0

        # Keep only the most recent IDs (approximate by removing oldest)
        # Since we don't track timestamps per ID, we just keep a subset
        ids_list = list(state.seen_ids)
        removed_count = len(ids_list) - max_ids
        state.seen_ids = set(ids_list[-max_ids:])
        return removed_count

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "searches": {name: state.to_dict() for name, state in self.searches.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppState":
        version = data.get("version", 1)
        searches = {}
        for name, state_data in data.get("searches", {}).items():
            searches[name] = SearchState.from_dict(state_data)
        return cls(searches=searches, version=version)


class StateManager:
    """Manages persistence of application state to disk."""

    def __init__(self, state_file: str | Path = DEFAULT_STATE_FILE):
        self.state_file = Path(state_file)
        self._state: Optional[AppState] = None

    @property
    def state(self) -> AppState:
        """Get the current state, loading from disk if needed."""
        if self._state is None:
            self._state = self.load()
        return self._state

    def load(self) -> AppState:
        """Load state from disk, or create empty state if file doesn't exist."""
        if not self.state_file.exists():
            logger.info("No state file found at %s, starting fresh", self.state_file)
            return AppState()

        try:
            with self.state_file.open() as f:
                data = json.load(f)
            logger.info("Loaded state from %s", self.state_file)
            return AppState.from_dict(data)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load state from %s: %s. Starting fresh.", self.state_file, e)
            return AppState()

    def save(self) -> None:
        """Save current state to disk."""
        if self._state is None:
            return

        # Ensure directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with self.state_file.open("w") as f:
                json.dump(self._state.to_dict(), f, indent=2)
            logger.debug("Saved state to %s", self.state_file)
        except OSError as e:
            logger.error("Failed to save state to %s: %s", self.state_file, e)

    def is_seen(self, search_name: str, listing_id: str) -> bool:
        """Check if a listing has been seen."""
        return self.state.is_seen(search_name, listing_id)

    def mark_seen(self, search_name: str, listing_id: str) -> None:
        """Mark a listing as seen."""
        self.state.mark_seen(search_name, listing_id)

    def mark_notified(self, search_name: str) -> None:
        """Update the last notification time."""
        self.state.mark_notified(search_name)

    def can_notify(self, search_name: str, cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES) -> bool:
        """Check if notification is allowed based on cooldown."""
        return self.state.can_notify(search_name, cooldown_minutes)

    def get_time_until_notify(self, search_name: str, cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES) -> Optional[int]:
        """Get seconds until notification is allowed."""
        return self.state.get_time_until_notify(search_name, cooldown_minutes)

    def cleanup(self, max_ids_per_search: int = 1000) -> None:
        """Clean up old listing IDs from all searches."""
        for search_name in self.state.searches:
            removed = self.state.cleanup_old_ids(search_name, max_ids_per_search)
            if removed > 0:
                logger.info("Cleaned up %d old IDs from search '%s'", removed, search_name)


# Global state manager instance
_state_manager: Optional[StateManager] = None


def get_state_manager(state_file: str | Path = DEFAULT_STATE_FILE) -> StateManager:
    """Get or create the global state manager."""
    global _state_manager
    if _state_manager is None:
        # Check for environment variable override
        state_path = os.getenv("STATE_FILE", str(state_file))
        _state_manager = StateManager(state_path)
    return _state_manager
