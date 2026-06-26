"""Markov Chains attribution via the Removal Effect (PRD RF3.4).

A first-order Markov chain is built over states ``Start``, the marketing
channels and two absorbing states ``Conversion`` / ``Null``. The baseline
conversion probability ``P(conv)`` is computed analytically from the absorption
probabilities of the chain (fundamental matrix). The *Removal Effect* of a
channel is the relative drop in conversion probability when that channel is
removed from the graph; credits are the removal effects normalised so they sum
to the total number of conversions.

Reference formula (PRD Appendix A):

    RE_i = 1 - P(conv | without channel_i) / P(conv)
"""

from __future__ import annotations

import logging
from collections import defaultdict

import networkx as nx
import numpy as np
import pandas as pd

from src.models.base import AttributionModel, build_output, journey_sequences

logger = logging.getLogger("attribution.markov")

START = "Start"
CONVERSION = "Conversion"
NULL = "Null"
ABSORBING = (CONVERSION, NULL)

#: Transitions are keyed by ``(source, target)`` state strings.
TransitionCounts = dict[tuple[str, str], float]


def _record_transitions(
    paths: list[list[str]],
    converted: list[bool],
) -> TransitionCounts:
    """Accumulate transition counts from journey paths (networkx graph edges)."""
    counts: TransitionCounts = defaultdict(float)
    for path, is_converted in zip(paths, converted, strict=True):
        if not path:
            continue
        prev = START
        for channel in path:
            counts[(prev, channel)] += 1.0
            prev = channel
        counts[(prev, CONVERSION if is_converted else NULL)] += 1.0
    return counts


def _states(counts: TransitionCounts) -> set[str]:
    return {state for edge in counts for state in edge}


def _conversion_probability(
    counts: TransitionCounts,
    removed: str | None = None,
) -> float:
    """Analytical conversion probability from ``Start`` for the (reduced) chain."""
    all_states = _states(counts)
    transient = [START] + sorted(
        s for s in all_states if s not in (START, *ABSORBING) and s != removed
    )
    if START not in transient:
        return 0.0

    idx_t = {s: i for i, s in enumerate(transient)}
    absorbing = [CONVERSION, NULL]
    idx_a = {s: i for i, s in enumerate(absorbing)}
    n = len(transient)

    out_total: dict[str, float] = {s: 0.0 for s in transient}
    filtered: TransitionCounts = {}
    for (src, dst), count in counts.items():
        if src == removed or dst == removed:
            continue
        if src not in idx_t:
            continue
        filtered[(src, dst)] = count
        out_total[src] += count

    q = np.zeros((n, n))
    r = np.zeros((n, len(absorbing)))
    for (src, dst), count in filtered.items():
        total = out_total[src]
        if total <= 0:
            continue
        prob = count / total
        if dst in idx_t:
            q[idx_t[src], idx_t[dst]] = prob
        elif dst in idx_a:
            r[idx_t[src], idx_a[dst]] = prob

    # A transient state whose only successor was removed now leads nowhere;
    # route it to Null so the chain stays absorbing (journey ends, no conversion).
    for state, total in out_total.items():
        if total <= 0:
            r[idx_t[state], idx_a[NULL]] = 1.0

    try:
        fundamental = np.linalg.inv(np.eye(n) - q)
    except np.linalg.LinAlgError:
        return 0.0
    absorption = fundamental @ r
    return float(absorption[idx_t[START], idx_a[CONVERSION]])


def _removal_effects(paths: list[list[str]], converted: list[bool]) -> dict[str, float]:
    """Compute the removal effect for every channel that appears in a path."""
    counts = _record_transitions(paths, converted)
    baseline = _conversion_probability(counts)
    channels = sorted({channel for path in paths for channel in path})

    effects: dict[str, float] = {}
    for channel in channels:
        without = _conversion_probability(counts, removed=channel)
        if baseline <= 0:
            effects[channel] = 0.0
        else:
            drop = (baseline - without) / baseline
            effects[channel] = max(0.0, drop)
    logger.info(
        "markov.removal_effect baseline=%.4f channels=%d effects_sum=%.4f",
        baseline,
        len(channels),
        sum(effects.values()),
    )
    return effects


def build_transition_graph(paths: list[list[str]], converted: list[bool]) -> nx.DiGraph:
    """Expose the weighted transition graph (used by tests / dashboards)."""
    counts = _record_transitions(paths, converted)
    graph = nx.DiGraph()
    for (src, dst), weight in counts.items():
        graph.add_edge(src, dst, weight=float(weight))
    return graph


class MarkovChainsModel(AttributionModel):
    """Markov Chains attribution with the Removal Effect (RF3.4)."""

    def __init__(self) -> None:
        super().__init__("markov")

    def attribute(self, journeys: pd.DataFrame) -> pd.DataFrame:
        paths, converted, revenues = journey_sequences(journeys)
        total_conversions = float(sum(converted))
        total_revenue = float(sum(r for r, c in zip(revenues, converted, strict=True) if c))
        channels = sorted({channel for path in paths for channel in path})

        if total_conversions <= 0 or not channels:
            return build_output({}, {}, channels)

        effects = _removal_effects(paths, converted)
        total_effect = sum(effects.values())

        conversions: dict[str, float] = {}
        revenue: dict[str, float] = {}
        for channel in channels:
            share = effects[channel] / total_effect if total_effect > 0 else 1.0 / len(channels)
            conversions[channel] = share * total_conversions
            revenue[channel] = share * total_revenue
        return build_output(conversions, revenue, channels)


__all__: tuple[str, ...] = (
    "MarkovChainsModel",
    "build_transition_graph",
    "START",
    "CONVERSION",
    "NULL",
)
