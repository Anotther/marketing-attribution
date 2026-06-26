"""Tests for :mod:`src.ingestion` (PRD RF1.1-RF1.4)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import pytest
from src.ingestion import (
    EXPECTED_RAW_COLUMNS,
    REVENUE_MICROS_DIVISOR,
    BigQueryIngester,
    IngestionError,
    SchemaError,
    build_extraction_query,
    build_query_parameters,
    clean_sessions,
)


class TestExtractionQuery:
    def test_selects_all_required_fields(self) -> None:
        sql = build_extraction_query("bigquery-public-data.google_analytics_sample")
        for field_ in ("fullVisitorId", "channelGrouping", "visitNumber", "date"):
            assert field_ in sql
        assert "totals.transactions" in sql
        assert "totals.transactionRevenue" in sql

    def test_filters_by_table_suffix_window(self) -> None:
        sql = build_extraction_query("my-project.my_dataset")
        assert "@start_date" in sql
        assert "@end_date" in sql
        assert "_TABLE_SUFFIX BETWEEN" in sql

    def test_uses_configured_dataset(self) -> None:
        sql = build_extraction_query("proj.ds")
        assert "`proj.ds.ga_sessions_*`" in sql


class TestQueryParameters:
    def test_parameters_are_string_yyyymmdd(self) -> None:
        params = build_query_parameters(date(2016, 8, 1), date(2017, 8, 1))
        assert len(params) == 2
        names = [p.name for p in params]
        assert names == ["start_date", "end_date"]
        values = [p.value for p in params]
        assert values == ["20160801", "20170801"]


class TestCleanSessions:
    def test_drops_null_visitor_and_logs(self, ga_raw_sessions, caplog) -> None:  # type: ignore[no-untyped-def]
        caplog.set_level("WARNING", logger="attribution.ingestion")
        cleaned = clean_sessions(ga_raw_sessions)
        assert len(cleaned) == 3
        assert any("null_visitor" in r.message for r in caplog.records)

    def test_revenue_converted_from_micros(self, ga_raw_sessions) -> None:  # type: ignore[no-untyped-def]
        cleaned = clean_sessions(ga_raw_sessions.reset_index(drop=True))
        # Row 0: 50_000_000 micros -> 50.0 dollars; row 2: 0 -> 0.0
        revenue = cleaned["transactionRevenue"].tolist()
        assert revenue[0] == pytest.approx(50.0)
        assert revenue[1] == pytest.approx(0.0)

    def test_transactions_filled_and_integer(self, ga_raw_sessions) -> None:  # type: ignore[no-untyped-def]
        cleaned = clean_sessions(ga_raw_sessions)
        assert cleaned["transactions"].dtype == "int64"
        # None -> 0
        assert 0 in cleaned["transactions"].tolist()

    def test_date_parsed_to_datetime(self, ga_raw_sessions) -> None:  # type: ignore[no-untyped-def]
        cleaned = clean_sessions(ga_raw_sessions)
        assert pd.api.types.is_datetime64_any_dtype(cleaned["date"])

    def test_does_not_mutate_input(self, ga_raw_sessions) -> None:  # type: ignore[no-untyped-def]
        original = ga_raw_sessions.copy(deep=True)
        clean_sessions(ga_raw_sessions)
        pd.testing.assert_frame_equal(ga_raw_sessions, original)

    def test_returns_canonical_column_order(self, ga_raw_sessions) -> None:  # type: ignore[no-untyped-def]
        cleaned = clean_sessions(ga_raw_sessions)
        assert tuple(cleaned.columns) == EXPECTED_RAW_COLUMNS

    def test_missing_column_raises_schema_error(self) -> None:
        bad = pd.DataFrame({"fullVisitorId": ["x"], "channelGrouping": ["c"]})
        with pytest.raises(SchemaError, match="missing expected columns"):
            clean_sessions(bad)

    def test_bad_date_rows_dropped(self, caplog) -> None:  # type: ignore[no-untyped-def]
        df = pd.DataFrame(
            {
                "fullVisitorId": ["a", "b"],
                "channelGrouping": ["c", "c"],
                "visitNumber": [1, 1],
                "date": ["20160801", "not-a-date"],
                "transactions": [0, 0],
                "transactionRevenue": [0, 0],
            }
        )
        caplog.set_level("WARNING", logger="attribution.ingestion")
        cleaned = clean_sessions(df)
        assert len(cleaned) == 1
        assert any("bad_date" in r.message for r in caplog.records)

    def test_micros_divisor_constant(self) -> None:
        assert REVENUE_MICROS_DIVISOR == 1_000_000


class FakeJob:
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    def to_dataframe(self) -> pd.DataFrame:
        return self._df


class FlakyClient:
    """BigQuery-shaped client that fails N times then succeeds."""

    def __init__(self, df: pd.DataFrame, fail_times: int, exc: type[Exception]) -> None:
        self._df = df
        self._fail_times = fail_times
        self._calls = 0
        self._exc = exc
        self.last_job_config: Any = None

    def query(self, query: str, job_config: Any = None) -> FakeJob:  # noqa: D401
        self._calls += 1
        self.last_job_config = job_config
        if self._calls <= self._fail_times:
            raise self._exc("transient failure")
        return FakeJob(self._df)


class TestBigQueryIngester:
    def _raw(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "fullVisitorId": ["111", "222"],
                "channelGrouping": ["Organic Search", "Direct"],
                "visitNumber": [1, 2],
                "date": ["20160801", "20160802"],
                "transactions": [1, 0],
                "transactionRevenue": [50_000_000, 0],
            }
        )

    def test_run_cleans_extracted_rows(self) -> None:
        client = FlakyClient(self._raw(), fail_times=0, exc=RuntimeError)
        ingester = BigQueryIngester(
            client=client,
            dataset="proj.ds",
            start=date(2016, 8, 1),
            end=date(2017, 8, 1),
            max_retries=3,
        )
        df = ingester.run()
        assert len(df) == 2
        assert df["transactionRevenue"].iloc[0] == pytest.approx(50.0)

    def test_retry_then_success(self) -> None:
        client = FlakyClient(self._raw(), fail_times=2, exc=ConnectionError)
        sleeps: list[float] = []
        ingester = BigQueryIngester(
            client=client,
            dataset="proj.ds",
            start=date(2016, 8, 1),
            end=date(2017, 8, 1),
            max_retries=3,
            sleep=sleeps.append,
            backoff_base=2.0,
        )
        df = ingester.run()
        assert len(df) == 2
        assert client._calls == 3
        # exponential backoff: 2^0, 2^1 -> [1.0, 2.0]
        assert sleeps == [1.0, 2.0]

    def test_exhausts_retries_raises_ingestion_error(self) -> None:
        client = FlakyClient(self._raw(), fail_times=99, exc=ConnectionError)
        ingester = BigQueryIngester(
            client=client,
            dataset="proj.ds",
            start=date(2016, 8, 1),
            end=date(2017, 8, 1),
            max_retries=2,
            sleep=lambda _s: None,
        )
        with pytest.raises(IngestionError, match="after 2 attempts"):
            ingester.run()
        assert client._calls == 2

    def test_query_uses_parameters(self) -> None:
        client = FlakyClient(self._raw(), fail_times=0, exc=RuntimeError)
        ingester = BigQueryIngester(
            client=client,
            dataset="proj.ds",
            start=date(2016, 8, 1),
            end=date(2017, 8, 1),
        )
        ingester.run()
        job_config = client.last_job_config
        param_names = [p.name for p in job_config.query_parameters]
        assert param_names == ["start_date", "end_date"]
