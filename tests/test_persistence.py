"""Tests for :mod:`src.persistence` (PRD RF4.1-RF4.6)."""

from __future__ import annotations

import pandas as pd
import pytest
from src.models import attribute_full
from src.persistence import (
    FATO_JOURNEYS_PARQUET,
    RESULTADOS_PARQUET,
    persist,
    persist_all,
)
from src.preprocessing import build_journeys


@pytest.fixture
def journeys(multi_session_clean: pd.DataFrame) -> pd.DataFrame:
    return build_journeys(multi_session_clean)


@pytest.fixture
def results_full(journeys: pd.DataFrame) -> pd.DataFrame:
    return attribute_full(journeys)


@pytest.fixture
def artifacts(journeys, results_full, tmp_path):  # type: ignore[no-untyped-def]
    # Use SQLite in-memory database for testing the SQLAlchemy logic
    db_url = "sqlite:///:memory:"
    return persist(
        journeys,
        results_full,
        db_url=db_url,
        parquet_dir=tmp_path,
    )


class TestPostgresStore:
    def test_returns_artifact_paths(self, artifacts, tmp_path) -> None:  # type: ignore[no-untyped-def]
        assert "postgres" in artifacts
        assert artifacts["resultados_atribuicao"] == str(tmp_path / RESULTADOS_PARQUET)
        assert artifacts["fato_jornadas"] == str(tmp_path / FATO_JOURNEYS_PARQUET)


class TestIdempotency:
    def test_rerun_does_not_duplicate(self, journeys, results_full, tmp_path) -> None:  # type: ignore[no-untyped-def]
        db_url = "sqlite:///:memory:"
        kwargs = {"db_url": db_url, "parquet_dir": tmp_path}
        persist(journeys, results_full, **kwargs)
        persist(journeys, results_full, **kwargs)
        
        df_fato = pd.read_parquet(tmp_path / FATO_JOURNEYS_PARQUET)
        assert len(df_fato) == 3


class TestParquetExport:
    def test_resultados_readable_by_pandas(self, artifacts, tmp_path) -> None:  # type: ignore[no-untyped-def]
        df = pd.read_parquet(tmp_path / RESULTADOS_PARQUET)
        assert len(df) == 6
        assert "first_click_credit" in df.columns
        assert "shapley_revenue" in df.columns

    def test_fato_journeys_readable_by_pandas(self, artifacts, tmp_path) -> None:  # type: ignore[no-untyped-def]
        df = pd.read_parquet(tmp_path / FATO_JOURNEYS_PARQUET)
        assert len(df) == 3
        assert "channel_path" in df.columns


class TestPersistAll:
    def test_writes_under_data_dir(self, journeys, results_full, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
        artifacts = persist_all(journeys, results_full, str(tmp_path))
        assert (tmp_path / RESULTADOS_PARQUET).exists()
        assert artifacts["postgres"] == "sqlite:///:memory:"
