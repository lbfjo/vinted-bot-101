from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.fetcher.vinted import Listing


@dataclass
class RuleContext:
    rule_name: str
    locale: str


class Notifier(Protocol):
    def send(self, listing: Listing, context: RuleContext) -> None:
        ...
