"""Abstract interface for attribution models (PRD section 5, Module 3).

All attribution models accept a *journeys* dataframe (as produced by
:mod:`src.preprocessing`, matching ``fato_jornadas``) and return a dataframe with
columns ``channel``, ``conversions`` and ``revenue`` -- the per-channel credit
each model assigns. The invariant enforced downstream (PRD RF3.1-RF3.5) is that
the returned ``conversions`` credits sum to the total number of converting
journeys.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypedDict

import pandas as pd

#: Canonical journey dataframe columns consumed by every model.
JOURNEY_COLUMNS: tuple[str, ...] = (
    "channel_path",
    "converted",
    "transaction_revenue",
)

#: Canonical output columns every model returns.
MODEL_OUTPUT_COLUMNS: tuple[str, ...] = ("channel", "conversions", "revenue")


class Journeys(TypedDict, total=False):
    """Structural hint for the journey dataframe contract."""

    channel_path: pd.Series
    converted: pd.Series
    transaction_revenue: pd.Series


class AttributionResult(TypedDict, total=False):
    """Structural hint for a model's attribution output dataframe."""

    channel: pd.Series
    conversions: pd.Series
    revenue: pd.Series


class AttributionModelError(ValueError):
    """Raised when a journeys dataframe does not match the model contract."""


def validate_journeys(journeys: pd.DataFrame) -> None:
    """Ensure a journeys dataframe exposes the columns models need."""
    missing = [c for c in JOURNEY_COLUMNS if c not in journeys.columns]
    if missing:
        raise AttributionModelError(f"journeys missing required columns: {missing}")


def journey_sequences(
    journeys: pd.DataFrame,
) -> tuple[list[list[str]], list[bool], list[float]]:
    """Extract ``(paths, converted_flags, revenues)`` lists from journeys."""
    validate_journeys(journeys)
    paths = [list(p) for p in journeys["channel_path"].tolist()]
    converted = [bool(c) for c in journeys["converted"].tolist()]
    revenues = [float(r) for r in journeys["transaction_revenue"].tolist()]
    return paths, converted, revenues


def build_output(
    conversions: dict[str, float],
    revenue: dict[str, float],
    channels: list[str],
) -> pd.DataFrame:
    """Assemble the canonical ``[channel, conversions, revenue]`` output frame."""
    rows = [
        {
            "channel": ch,
            "conversions": float(conversions.get(ch, 0.0)),
            "revenue": float(revenue.get(ch, 0.0)),
        }
        for ch in channels
    ]
    return pd.DataFrame(rows, columns=list(MODEL_OUTPUT_COLUMNS))


class AttributionModel(ABC):
    """Common contract for every attribution model.

    Subclasses set :attr:`name` (the consolidation column key) and implement
    :meth:`attribute`.
    """

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def attribute(self, journeys: pd.DataFrame) -> pd.DataFrame:
        """Compute per-channel attribution credits for ``journeys``.

        Returns:
            A dataframe with ``channel``, ``conversions`` and ``revenue`` columns
            whose ``conversions`` credits sum to the number of converting
            journeys.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
