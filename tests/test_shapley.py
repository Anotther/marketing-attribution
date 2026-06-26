"""Tests for :mod:`src.models.shapley` (PRD RF3.5).

Canonical example (hand-derived): converting paths {A} x1 and {A,B} x1.
  phi_A = 1.5, phi_B = 0.5  (sum = 2 = total conversions -> efficiency).
"""

from __future__ import annotations

import pandas as pd
import pytest
from src.models.shapley import ShapleyValueModel, _coalition_values, _shapley_values


@pytest.fixture
def canonical_journeys() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "channel_path": [["A"], ["A", "B"]],
            "converted": [True, True],
            "transaction_revenue": [0.0, 0.0],
        }
    )


def _credit(df: pd.DataFrame, channel: str) -> float:
    return float(df.loc[df["channel"] == channel, "conversions"].iloc[0])


class TestCoalitionValues:
    def test_counts_converting_path_sets(self) -> None:
        paths = [["A"], ["A", "B"], ["A", "B"]]
        converted = [True, True, False]
        coalitions = _coalition_values(paths, converted)
        assert coalitions[frozenset({"A"})] == 1
        assert coalitions[frozenset({"A", "B"})] == 1  # only the converting one


class TestShapleyValues:
    def test_known_shapley_values(self) -> None:
        coalitions = _coalition_values([["A"], ["A", "B"]], [True, True])
        shapley = _shapley_values(coalitions, ["A", "B"])
        assert shapley["A"] == pytest.approx(1.5)
        assert shapley["B"] == pytest.approx(0.5)

    def test_efficiency(self) -> None:
        coalitions = _coalition_values([["A"], ["A", "B"], ["B", "C"]], [True, True, True])
        shapley = _shapley_values(coalitions, ["A", "B", "C"])
        assert sum(shapley.values()) == pytest.approx(3.0)

    def test_null_player_gets_zero(self) -> None:
        # 'C' only appears in non-converting paths.
        coalitions = _coalition_values([["A"], ["C"]], [True, False])
        shapley = _shapley_values(coalitions, ["A", "C"])
        assert shapley["C"] == pytest.approx(0.0)
        assert shapley["A"] == pytest.approx(1.0)

    def test_symmetric_players_share_equally(self) -> None:
        # Two channels that are perfectly interchangeable across conversions.
        coalitions = _coalition_values([["A", "B"], ["B", "A"]], [True, True])
        shapley = _shapley_values(coalitions, ["A", "B"])
        assert shapley["A"] == pytest.approx(shapley["B"])
        assert shapley["A"] + shapley["B"] == pytest.approx(2.0)


class TestShapleyModel:
    def test_credits_match_hand_calc(self, canonical_journeys) -> None:  # type: ignore[no-untyped-def]
        result = ShapleyValueModel().attribute(canonical_journeys)
        assert _credit(result, "A") == pytest.approx(1.5)
        assert _credit(result, "B") == pytest.approx(0.5)

    def test_credits_sum_to_conversions(self, canonical_journeys) -> None:  # type: ignore[no-untyped-def]
        result = ShapleyValueModel().attribute(canonical_journeys)
        assert result["conversions"].sum() == pytest.approx(2.0)

    def test_no_conversions_returns_zero_credits(self) -> None:
        journeys = pd.DataFrame(
            {
                "channel_path": [["A", "B"]],
                "converted": [False],
                "transaction_revenue": [0.0],
            }
        )
        result = ShapleyValueModel().attribute(journeys)
        assert result["conversions"].sum() == pytest.approx(0.0)

    def test_revenue_proportional(self) -> None:
        journeys = pd.DataFrame(
            {
                "channel_path": [["A"], ["A", "B"]],
                "converted": [True, True],
                "transaction_revenue": [60.0, 40.0],
            }
        )
        result = ShapleyValueModel().attribute(journeys)
        total = result["revenue"].sum()
        assert total == pytest.approx(100.0)
        # A holds 75% of credit -> 75% of revenue.
        assert result.loc[result["channel"] == "A", "revenue"].iloc[0] == pytest.approx(75.0)
