"""Tests for :mod:`src.models.heuristics` (PRD RF3.1-RF3.3)."""

from __future__ import annotations

import pandas as pd
import pytest
from src.models.heuristics import (
    first_click_model,
    last_click_model,
    linear_model,
)


@pytest.fixture
def journeys_df() -> pd.DataFrame:
    """Three converting journeys with known positional credits.

    J1=[A,B,C] rev=30, J2=[A] rev=10, J3=[B,A] rev=20. Total conversions=3.
    """
    return pd.DataFrame(
        {
            "channel_path": [["A", "B", "C"], ["A"], ["B", "A"]],
            "converted": [True, True, True],
            "transaction_revenue": [30.0, 10.0, 20.0],
        }
    )


def _credit(df: pd.DataFrame, channel: str) -> float:
    return float(df.loc[df["channel"] == channel, "conversions"].iloc[0])


def _revenue(df: pd.DataFrame, channel: str) -> float:
    return float(df.loc[df["channel"] == channel, "revenue"].iloc[0])


class TestFirstClick:
    def test_credits_first_touchpoint(self, journeys_df) -> None:  # type: ignore[no-untyped-def]
        result = first_click_model().attribute(journeys_df)
        assert _credit(result, "A") == pytest.approx(2.0)  # J1, J2
        assert _credit(result, "B") == pytest.approx(1.0)  # J3
        assert _credit(result, "C") == pytest.approx(0.0)

    def test_credits_sum_to_conversions(self, journeys_df) -> None:  # type: ignore[no-untyped-def]
        result = first_click_model().attribute(journeys_df)
        assert result["conversions"].sum() == pytest.approx(3.0)

    def test_revenue_follows_first_channel(self, journeys_df) -> None:  # type: ignore[no-untyped-def]
        result = first_click_model().attribute(journeys_df)
        assert _revenue(result, "A") == pytest.approx(40.0)  # 30 + 10
        assert _revenue(result, "B") == pytest.approx(20.0)
        assert result["revenue"].sum() == pytest.approx(60.0)


class TestLastClick:
    def test_credits_last_touchpoint(self, journeys_df) -> None:  # type: ignore[no-untyped-def]
        result = last_click_model().attribute(journeys_df)
        assert _credit(result, "C") == pytest.approx(1.0)  # J1
        assert _credit(result, "A") == pytest.approx(2.0)  # J2, J3
        assert result["conversions"].sum() == pytest.approx(3.0)


class TestLinear:
    def test_equal_split(self, journeys_df) -> None:  # type: ignore[no-untyped-def]
        result = linear_model().attribute(journeys_df)
        # J1: A,B,C each 1/3 ; J2: A=1 ; J3: B,A each 1/2
        assert _credit(result, "A") == pytest.approx(1 / 3 + 1 + 1 / 2)
        assert _credit(result, "B") == pytest.approx(1 / 3 + 1 / 2)
        assert _credit(result, "C") == pytest.approx(1 / 3)
        assert result["conversions"].sum() == pytest.approx(3.0)

    def test_single_channel_path_gets_full_credit(self) -> None:
        journeys = pd.DataFrame(
            {"channel_path": [["A"]], "converted": [True], "transaction_revenue": [5.0]}
        )
        result = linear_model().attribute(journeys)
        assert _credit(result, "A") == pytest.approx(1.0)


class TestNonConvertingIgnored:
    def test_non_converting_journey_gets_no_credit(self) -> None:
        journeys = pd.DataFrame(
            {
                "channel_path": [["A", "B"], ["A"]],
                "converted": [True, False],
                "transaction_revenue": [10.0, 0.0],
            }
        )
        for factory in (first_click_model, last_click_model, linear_model):
            result = factory().attribute(journeys)
            assert result["conversions"].sum() == pytest.approx(1.0)


class TestOutputSchema:
    def test_columns_and_dtypes(self, journeys_df) -> None:  # type: ignore[no-untyped-def]
        result = first_click_model().attribute(journeys_df)
        assert list(result.columns) == ["channel", "conversions", "revenue"]
        assert result["conversions"].dtype == "float64"
