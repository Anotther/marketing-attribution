"""Tests for :mod:`src.preprocessing` (PRD RF2.1-RF2.3)."""

from __future__ import annotations

import pandas as pd
import pytest
from src.preprocessing import (
    DIM_CANAIS_COLUMNS,
    JOURNEY_COLUMNS,
    PreprocessingError,
    build_channel_dimension,
    build_journeys,
    journey_stats,
)


class TestBuildJourneys:
    def test_groups_sessions_into_journeys(self, multi_session_clean) -> None:  # type: ignore[no-untyped-def]
        journeys = build_journeys(multi_session_clean)
        assert list(journeys.columns) == list(JOURNEY_COLUMNS)
        assert len(journeys) == 3
        assert journeys["visitor_id"].tolist() == ["V1", "V2", "V3"]

    def test_channel_path_ordered_by_date(self, multi_session_clean) -> None:  # type: ignore[no-untyped-def]
        # Shuffle input rows; path must still come out date-ordered.
        shuffled = multi_session_clean.sample(frac=1, random_state=42)
        journeys = build_journeys(shuffled).set_index("visitor_id")
        assert journeys.loc["V1", "channel_path"] == ["Organic Search", "Social", "Paid Search"]
        assert journeys.loc["V2", "channel_path"] == ["Direct", "Referral"]
        assert journeys.loc["V3", "channel_path"] == ["Display"]

    def test_path_length_matches_path(self, multi_session_clean) -> None:  # type: ignore[no-untyped-def]
        journeys = build_journeys(multi_session_clean).set_index("visitor_id")
        assert journeys.loc["V1", "path_length"] == 3
        assert journeys.loc["V2", "path_length"] == 2

    def test_converted_flag_from_transactions(self, multi_session_clean) -> None:  # type: ignore[no-untyped-def]
        journeys = build_journeys(multi_session_clean).set_index("visitor_id")
        assert bool(journeys.loc["V1", "converted"]) is True
        assert bool(journeys.loc["V2", "converted"]) is False
        assert bool(journeys.loc["V3", "converted"]) is True

    def test_revenue_summed_per_journey(self, multi_session_clean) -> None:  # type: ignore[no-untyped-def]
        journeys = build_journeys(multi_session_clean).set_index("visitor_id")
        assert journeys.loc["V1", "transaction_revenue"] == pytest.approx(100.0)
        assert journeys.loc["V2", "transaction_revenue"] == pytest.approx(0.0)
        assert journeys.loc["V3", "transaction_revenue"] == pytest.approx(50.0)

    def test_journey_id_is_deterministic(self, multi_session_clean) -> None:  # type: ignore[no-untyped-def]
        a = build_journeys(multi_session_clean).set_index("visitor_id")
        b = build_journeys(multi_session_clean.sample(frac=1, random_state=1)).set_index(
            "visitor_id"
        )
        assert a.loc["V1", "journey_id"] == b.loc["V1", "journey_id"]

    def test_first_and_last_visit_dates(self, multi_session_clean) -> None:  # type: ignore[no-untyped-def]
        journeys = build_journeys(multi_session_clean).set_index("visitor_id")
        assert pd.Timestamp(journeys.loc["V1", "first_visit_date"]) == pd.Timestamp("2016-08-01")
        assert pd.Timestamp(journeys.loc["V1", "last_visit_date"]) == pd.Timestamp("2016-08-05")

    def test_empty_sessions_returns_empty_frame(self) -> None:
        empty = pd.DataFrame(
            columns=[
                "fullVisitorId",
                "channelGrouping",
                "visitNumber",
                "date",
                "transactions",
                "transactionRevenue",
            ]
        )
        journeys = build_journeys(empty)
        assert journeys.empty
        assert list(journeys.columns) == list(JOURNEY_COLUMNS)

    def test_missing_columns_raises(self) -> None:
        with pytest.raises(PreprocessingError, match="missing columns"):
            build_journeys(pd.DataFrame({"fullVisitorId": ["x"]}))


class TestJourneyStats:
    def test_stats_aggregates(self, multi_session_clean) -> None:  # type: ignore[no-untyped-def]
        journeys = build_journeys(multi_session_clean)
        stats = journey_stats(journeys)
        assert stats["total_journeys"] == 3.0
        assert stats["total_conversions"] == 2.0
        assert stats["conversion_rate"] == pytest.approx(2 / 3)
        assert stats["avg_path_length"] == pytest.approx((3 + 2 + 1) / 3)
        assert stats["unique_channels"] == 6.0

    def test_stats_empty(self) -> None:
        empty = build_journeys(
            pd.DataFrame(
                columns=[
                    "fullVisitorId",
                    "channelGrouping",
                    "visitNumber",
                    "date",
                    "transactions",
                    "transactionRevenue",
                ]
            )
        )
        stats = journey_stats(empty)
        assert stats["total_journeys"] == 0.0
        assert stats["conversion_rate"] == 0.0


class TestChannelDimension:
    def test_columns_and_channels(self, multi_session_clean) -> None:  # type: ignore[no-untyped-def]
        journeys = build_journeys(multi_session_clean)
        dim = build_channel_dimension(journeys)
        assert list(dim.columns) == list(DIM_CANAIS_COLUMNS)
        assert len(dim) == 6
        assert set(dim["channel_name"]) == {
            "Organic Search",
            "Social",
            "Paid Search",
            "Direct",
            "Referral",
            "Display",
        }

    def test_total_sessions_counts_touchpoints(self, multi_session_clean) -> None:  # type: ignore[no-untyped-def]
        journeys = build_journeys(multi_session_clean)
        dim = build_channel_dimension(journeys).set_index("channel_name")
        assert dim.loc["Paid Search", "total_sessions"] == 1
        assert dim.loc["Organic Search", "total_sessions"] == 1

    def test_conversions_counted_on_converting_journeys(self, multi_session_clean) -> None:  # type: ignore[no-untyped-def]
        journeys = build_journeys(multi_session_clean)
        dim = build_channel_dimension(journeys).set_index("channel_name")
        # Only V1 (Organic, Social, Paid) and V3 (Display) converted.
        assert dim.loc["Organic Search", "total_conversions"] == 1
        assert dim.loc["Social", "total_conversions"] == 1
        assert dim.loc["Display", "total_conversions"] == 1
        assert dim.loc["Direct", "total_conversions"] == 0

    def test_revenue_on_converting_journeys(self, multi_session_clean) -> None:  # type: ignore[no-untyped-def]
        journeys = build_journeys(multi_session_clean)
        dim = build_channel_dimension(journeys).set_index("channel_name")
        assert dim.loc["Paid Search", "total_revenue"] == pytest.approx(100.0)
        assert dim.loc["Display", "total_revenue"] == pytest.approx(50.0)
        assert dim.loc["Direct", "total_revenue"] == pytest.approx(0.0)

    def test_avg_position(self, multi_session_clean) -> None:  # type: ignore[no-untyped-def]
        journeys = build_journeys(multi_session_clean)
        dim = build_channel_dimension(journeys).set_index("channel_name")
        # V1 path [Organic(1), Social(2), Paid(3)] -> each appears once at its pos.
        assert dim.loc["Organic Search", "avg_position"] == pytest.approx(1.0)
        assert dim.loc["Social", "avg_position"] == pytest.approx(2.0)
        assert dim.loc["Paid Search", "avg_position"] == pytest.approx(3.0)

    def test_conversion_rate(self, multi_session_clean) -> None:  # type: ignore[no-untyped-def]
        journeys = build_journeys(multi_session_clean)
        dim = build_channel_dimension(journeys).set_index("channel_name")
        # Direct appears in 1 journey (V2, non-converting) -> rate 0.
        assert dim.loc["Direct", "conversion_rate"] == pytest.approx(0.0)
        # Organic appears in 1 journey (V1, converting) -> rate 1.
        assert dim.loc["Organic Search", "conversion_rate"] == pytest.approx(1.0)

    def test_empty_journeys(self) -> None:
        dim = build_channel_dimension(pd.DataFrame(columns=list(JOURNEY_COLUMNS)))
        assert dim.empty
        assert list(dim.columns) == list(DIM_CANAIS_COLUMNS)
