"""Journey assembly from cleaned sessions (PRD Module 2, RF2.1-RF2.3).

A *journey* is the ordered sequence of marketing channels a single visitor
touched, plus whether it converted and how much revenue it generated. The
schema matches the ``fato_jornadas`` table (PRD section 9.1) so the output flows
straight into persistence (M4) and the attribution models (M3).
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import pandas as pd

logger = logging.getLogger("attribution.preprocessing")

#: Columns the cleaned-session input must provide.
REQUIRED_SESSION_COLUMNS: tuple[str, ...] = (
    "fullVisitorId",
    "channelGrouping",
    "visitNumber",
    "date",
    "transactions",
    "transactionRevenue",
)

#: Columns of the produced journey dataframe (matches ``fato_jornadas``).
JOURNEY_COLUMNS: tuple[str, ...] = (
    "journey_id",
    "visitor_id",
    "channel_path",
    "path_length",
    "converted",
    "transaction_revenue",
    "first_visit_date",
    "last_visit_date",
)


class PreprocessingError(ValueError):
    """Raised when cleaned sessions do not match the expected schema."""


def _journey_id(visitor_id: Any) -> str:
    digest = hashlib.sha1(str(visitor_id).encode("utf-8")).hexdigest()
    return digest[:16]


def _validate_sessions(sessions: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_SESSION_COLUMNS if c not in sessions.columns]
    if missing:
        raise PreprocessingError(f"cleaned sessions missing columns: {missing}")


def build_journeys(sessions: pd.DataFrame) -> pd.DataFrame:
    """Group cleaned sessions into per-visitor channel journeys (RF2.1, RF2.2).

    Sessions are ordered by ``(date, visitNumber)`` per visitor; the resulting
    ``channel_path`` is the ordered list of ``channelGrouping`` values. A journey
    is ``converted`` when the sum of its transactions is positive (RF2.2).
    """
    _validate_sessions(sessions)
    if sessions.empty:
        logger.warning("preprocessing.empty no sessions to assemble")
        return pd.DataFrame(columns=list(JOURNEY_COLUMNS))

    ordered = sessions.sort_values(["fullVisitorId", "date", "visitNumber"], kind="mergesort")
    records: list[dict[str, Any]] = []
    for visitor, group in ordered.groupby("fullVisitorId", sort=False):
        path = [str(c) for c in group["channelGrouping"].tolist()]
        transactions = pd.to_numeric(group["transactions"], errors="coerce").fillna(0)
        revenue = pd.to_numeric(group["transactionRevenue"], errors="coerce").fillna(0.0)
        records.append(
            {
                "journey_id": _journey_id(visitor),
                "visitor_id": str(visitor),
                "channel_path": path,
                "path_length": len(path),
                "converted": bool(transactions.sum() > 0),
                "transaction_revenue": float(revenue.sum()),
                "first_visit_date": group["date"].min(),
                "last_visit_date": group["date"].max(),
            }
        )

    journeys = pd.DataFrame(records, columns=list(JOURNEY_COLUMNS))
    logger.info(
        "preprocessing.assembled journeys=%d conversions=%d",
        len(journeys),
        int(journeys["converted"].sum()),
    )
    return journeys


def journey_stats(journeys: pd.DataFrame) -> dict[str, float]:
    """Aggregate journey-level statistics (RF2.3)."""
    total = len(journeys)
    conversions = int(journeys["converted"].sum()) if total else 0
    unique_channels = {channel for path in journeys["channel_path"] for channel in path}
    return {
        "total_journeys": float(total),
        "total_conversions": float(conversions),
        "conversion_rate": (conversions / total) if total else 0.0,
        "avg_path_length": float(journeys["path_length"].mean()) if total else 0.0,
        "unique_channels": float(len(unique_channels)),
    }


#: Columns of the channel dimension (matches ``dim_canais``, PRD section 9.2).
DIM_CANAIS_COLUMNS: tuple[str, ...] = (
    "channel_name",
    "total_sessions",
    "total_conversions",
    "total_revenue",
    "avg_position",
    "conversion_rate",
)


def build_channel_dimension(journeys: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-channel metrics for the ``dim_canais`` table (PRD RF4.3).

    - ``total_sessions``: touchpoint occurrences of the channel across journeys;
    - ``total_conversions`` / ``total_revenue``: counted on converting journeys
      that contain the channel (each journey contributes once per channel);
    - ``avg_position``: mean 1-based position of the channel in its journeys;
    - ``conversion_rate``: conversions / journeys containing the channel.
    """
    if journeys.empty:
        return pd.DataFrame(columns=list(DIM_CANAIS_COLUMNS))

    sessions: dict[str, int] = {}
    conversions: dict[str, int] = {}
    revenue: dict[str, float] = {}
    position_sum: dict[str, float] = {}
    position_count: dict[str, int] = {}
    containing: dict[str, int] = {}

    for path, is_converted, rev in zip(
        journeys["channel_path"],
        journeys["converted"],
        journeys["transaction_revenue"],
        strict=True,
    ):
        seen: set[str] = set()
        for position, channel in enumerate(path, start=1):
            sessions[channel] = sessions.get(channel, 0) + 1
            position_sum[channel] = position_sum.get(channel, 0.0) + position
            position_count[channel] = position_count.get(channel, 0) + 1
            seen.add(channel)
        for channel in seen:
            containing[channel] = containing.get(channel, 0) + 1
            if is_converted:
                conversions[channel] = conversions.get(channel, 0) + 1
                revenue[channel] = revenue.get(channel, 0.0) + float(rev)

    rows = [
        {
            "channel_name": channel,
            "total_sessions": sessions.get(channel, 0),
            "total_conversions": conversions.get(channel, 0),
            "total_revenue": revenue.get(channel, 0.0),
            "avg_position": (position_sum[channel] / position_count[channel])
            if position_count.get(channel)
            else 0.0,
            "conversion_rate": (conversions.get(channel, 0) / containing[channel])
            if containing.get(channel)
            else 0.0,
        }
        for channel in sorted(sessions)
    ]
    logger.info(
        "preprocessing.dimension channels=%d conversions=%d",
        len(rows),
        sum(conversions.values()),
    )
    return pd.DataFrame(rows, columns=list(DIM_CANAIS_COLUMNS))
