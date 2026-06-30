"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest
from src.config import Settings


@pytest.fixture
def base_env() -> dict[str, str]:
    """Minimal valid environment for :class:`Settings`."""
    return {
        "GCP_PROJECT_ID": "test-project",
        "GOOGLE_APPLICATION_CREDENTIALS": "credentials/gcp-sa.json",
        "BQ_START_DATE": "2016-08-01",
        "BQ_END_DATE": "2017-08-01",
    }


@pytest.fixture
def settings(base_env: dict[str, str]) -> Settings:
    return Settings.from_env(base_env)


@pytest.fixture(autouse=True)
def _reset_logging() -> Iterator[None]:
    """Ensure each test starts with a fresh logging configuration."""
    import src.logging_setup as ls

    saved = ls._CONFIGURED
    yield
    ls._CONFIGURED = saved


@pytest.fixture
def isolated_env(base_env: dict[str, str]) -> Iterator[dict[str, str]]:
    """Patch ``os.environ`` so tests do not leak process state."""
    with patch.dict("os.environ", base_env, clear=True):
        yield base_env


@pytest.fixture
def ga_raw_sessions() -> pd.DataFrame:
    """Synthetic GA-shaped raw sessions (revenue in micros)."""
    return pd.DataFrame(
        {
            "fullVisitorId": ["111", "222", None, "333"],
            "channelGrouping": ["Organic Search", "Direct", "Social", "Paid Search"],
            "visitNumber": [1, 2, 1, 3],
            "date": ["20160801", "20160802", "20160803", "20160804"],
            "transactions": [1, None, 0, 2],
            "transactionRevenue": [50_000_000, None, 0, 1_250_000_00],
        }
    )


@pytest.fixture
def ga_clean_sessions() -> pd.DataFrame:
    """Already-cleaned sessions (revenue in dollars)."""
    return pd.DataFrame(
        {
            "fullVisitorId": ["111", "222"],
            "channelGrouping": ["Organic Search", "Direct"],
            "visitNumber": [1, 2],
            "date": pd.to_datetime(["2016-08-01", "2016-08-02"]),
            "transactions": [1, 0],
            "transactionRevenue": [50.0, 0.0],
        }
    )


class FakeIngester:
    """Stand-in ingester used to test orchestration without BigQuery."""

    def __init__(self, rows: pd.DataFrame | None = None) -> None:
        self._rows = rows if rows is not None else pd.DataFrame({"fullVisitorId": ["x", "y", "z"]})

    def run(self) -> pd.DataFrame:  # noqa: D401 - simple stand-in
        return self._rows


@pytest.fixture
def fake_ingester(ga_clean_sessions: pd.DataFrame) -> Any:
    return FakeIngester(ga_clean_sessions)


@pytest.fixture
def multi_session_clean() -> pd.DataFrame:
    """Cleaned sessions with multi-touch visitors (ordered by date within each)."""
    return pd.DataFrame(
        {
            "fullVisitorId": [
                "V1",
                "V1",
                "V1",
                "V2",
                "V2",
                "V3",
            ],
            "channelGrouping": [
                "Organic Search",
                "Social",
                "Paid Search",
                "Direct",
                "Referral",
                "Display",
            ],
            "visitNumber": [1, 2, 3, 1, 2, 1],
            "date": pd.to_datetime(
                [
                    "2016-08-01",
                    "2016-08-03",
                    "2016-08-05",
                    "2016-08-02",
                    "2016-08-04",
                    "2016-08-06",
                ]
            ),
            "transactions": [0, 0, 1, 0, 0, 1],
            "transactionRevenue": [0.0, 0.0, 100.0, 0.0, 0.0, 50.0],
        }
    )
