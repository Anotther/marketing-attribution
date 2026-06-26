"""Tests for :mod:`src.models.markov` (PRD RF3.4).

The canonical example is hand-derived:
  paths: [A,B] converted, [A] converted, [A] not converted.
  baseline P(conv) = 2/3 ; RE_A = 1.0 ; RE_B = 0.25
  credits (2 conversions): A = 1.6, B = 0.4.
"""

from __future__ import annotations

import pandas as pd
import pytest
from src.models.markov import (
    CONVERSION,
    NULL,
    START,
    MarkovChainsModel,
    _conversion_probability,
    _record_transitions,
    _removal_effects,
    build_transition_graph,
)


@pytest.fixture
def canonical_journeys() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "channel_path": [["A", "B"], ["A"], ["A"]],
            "converted": [True, True, False],
            "transaction_revenue": [0.0, 0.0, 0.0],
        }
    )


def _credit(df: pd.DataFrame, channel: str) -> float:
    return float(df.loc[df["channel"] == channel, "conversions"].iloc[0])


class TestTransitionGraph:
    def test_counts_include_start_and_absorbing_states(self, canonical_journeys) -> None:  # type: ignore[no-untyped-def]
        paths = canonical_journeys["channel_path"].tolist()
        converted = canonical_journeys["converted"].tolist()
        counts = _record_transitions(paths, converted)
        assert counts[(START, "A")] == 3.0
        assert counts[("A", "B")] == 1.0
        assert counts[("A", CONVERSION)] == 1.0
        assert counts[("A", NULL)] == 1.0
        assert counts[("B", CONVERSION)] == 1.0

    def test_build_transition_graph_edges(self, canonical_journeys) -> None:  # type: ignore[no-untyped-def]
        paths = canonical_journeys["channel_path"].tolist()
        converted = canonical_journeys["converted"].tolist()
        graph = build_transition_graph(paths, converted)
        assert graph.has_edge(START, "A")
        assert graph["A"]["B"]["weight"] == 1.0


class TestConversionProbability:
    def test_baseline_probability(self, canonical_journeys) -> None:  # type: ignore[no-untyped-def]
        paths = canonical_journeys["channel_path"].tolist()
        converted = canonical_journeys["converted"].tolist()
        counts = _record_transitions(paths, converted)
        assert _conversion_probability(counts) == pytest.approx(2 / 3)

    def test_removal_drops_probability(self, canonical_journeys) -> None:  # type: ignore[no-untyped-def]
        paths = canonical_journeys["channel_path"].tolist()
        converted = canonical_journeys["converted"].tolist()
        counts = _record_transitions(paths, converted)
        baseline = _conversion_probability(counts)
        without_a = _conversion_probability(counts, removed="A")
        without_b = _conversion_probability(counts, removed="B")
        assert without_a < baseline
        assert without_b < baseline


class TestRemovalEffects:
    def test_known_removal_effects(self, canonical_journeys) -> None:  # type: ignore[no-untyped-def]
        paths = canonical_journeys["channel_path"].tolist()
        converted = canonical_journeys["converted"].tolist()
        effects = _removal_effects(paths, converted)
        assert effects["A"] == pytest.approx(1.0)
        assert effects["B"] == pytest.approx(0.25)

    def test_removal_effects_non_negative(self) -> None:
        journeys = pd.DataFrame(
            {
                "channel_path": [["A", "B"], ["B", "A"]],
                "converted": [True, True],
                "transaction_revenue": [0.0, 0.0],
            }
        )
        effects = _removal_effects(
            journeys["channel_path"].tolist(), journeys["converted"].tolist()
        )
        assert all(v >= 0.0 for v in effects.values())


class TestMarkovModel:
    def test_credits_match_hand_calc(self, canonical_journeys) -> None:  # type: ignore[no-untyped-def]
        result = MarkovChainsModel().attribute(canonical_journeys)
        assert _credit(result, "A") == pytest.approx(1.6)
        assert _credit(result, "B") == pytest.approx(0.4)

    def test_credits_sum_to_conversions(self, canonical_journeys) -> None:  # type: ignore[no-untyped-def]
        result = MarkovChainsModel().attribute(canonical_journeys)
        assert result["conversions"].sum() == pytest.approx(2.0)

    def test_no_conversions_returns_zero_credits(self) -> None:
        journeys = pd.DataFrame(
            {
                "channel_path": [["A", "B"]],
                "converted": [False],
                "transaction_revenue": [0.0],
            }
        )
        result = MarkovChainsModel().attribute(journeys)
        assert result["conversions"].sum() == pytest.approx(0.0)

    def test_revenue_proportional(self) -> None:
        journeys = pd.DataFrame(
            {
                "channel_path": [["A", "B"], ["A"], ["A"]],
                "converted": [True, True, False],
                "transaction_revenue": [60.0, 40.0, 0.0],
            }
        )
        result = MarkovChainsModel().attribute(journeys)
        # total converting revenue = 100 ; A share = 0.8, B share = 0.2
        assert result.loc[result["channel"] == "A", "revenue"].iloc[0] == pytest.approx(80.0)
        assert result.loc[result["channel"] == "B", "revenue"].iloc[0] == pytest.approx(20.0)
