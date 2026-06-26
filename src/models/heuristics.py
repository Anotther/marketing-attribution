"""Heuristic attribution models: First-Click, Last-Click, Linear (RF3.1-RF3.3).

These are the positional baselines. For every *converting* journey the credit
(one conversion and its revenue) is distributed across the touchpoints of the
channel path according to a positional rule. Summed across journeys, the credits
of any heuristic sum to the total number of converting journeys (PRD RF3.1-3.3).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

import pandas as pd

from src.models.base import (
    AttributionModel,
    build_output,
    journey_sequences,
)

#: A positional selector returns ``[(channel, weight), ...]`` for one path,
#: where ``weight`` is the share of the journey's credit that channel receives.
Selector = Callable[[list[str]], list[tuple[str, float]]]


def _first(path: list[str]) -> list[tuple[str, float]]:
    return [(path[0], 1.0)] if path else []


def _last(path: list[str]) -> list[tuple[str, float]]:
    return [(path[-1], 1.0)] if path else []


def _linear(path: list[str]) -> list[tuple[str, float]]:
    if not path:
        return []
    share = 1.0 / len(path)
    return [(channel, share) for channel in path]


class PositionalModel(AttributionModel):
    """Generic positional heuristic driven by a :data:`Selector`."""

    def __init__(self, name: str, selector: Selector) -> None:
        super().__init__(name)
        self._selector = selector

    def attribute(self, journeys: pd.DataFrame) -> pd.DataFrame:
        paths, converted, revenues = journey_sequences(journeys)
        conversions: dict[str, float] = defaultdict(float)
        revenue: dict[str, float] = defaultdict(float)
        # Emit every channel that appears in any path so all models share an
        # identical channel set (required for the RF3.6 consolidation).
        channels: set[str] = {channel for path in paths for channel in path}

        for path, is_converted, rev in zip(paths, converted, revenues, strict=True):
            for channel, weight in self._selector(path):
                revenue[channel] += rev * weight
                if is_converted:
                    conversions[channel] += weight

        return build_output(conversions, revenue, sorted(channels))


def first_click_model() -> PositionalModel:
    """100% credit to the first touchpoint (RF3.1)."""
    return PositionalModel("first_click", _first)


def last_click_model() -> PositionalModel:
    """100% credit to the last touchpoint (RF3.2)."""
    return PositionalModel("last_click", _last)


def linear_model() -> PositionalModel:
    """Equal credit across all touchpoints (RF3.3)."""
    return PositionalModel("linear", _linear)
