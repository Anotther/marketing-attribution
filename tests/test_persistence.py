"""Tests for :mod:`src.persistence` (PRD RF4.1-RF4.6)."""

from __future__ import annotations

import duckdb
import pandas as pd
import pytest
from src.models import attribute_full
from src.persistence import (
    DB_FILENAME,
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
    db_path = tmp_path / DB_FILENAME
    return persist(
        journeys,
        results_full,
        db_path=db_path,
        parquet_dir=tmp_path,
        connection=duckdb.connect(str(db_path)),
    )


class TestDuckDBStore:
    def test_creates_duckdb_file(self, journeys, results_full, tmp_path) -> None:  # type: ignore[no-untyped-def]
        db_path = tmp_path / DB_FILENAME
        persist(journeys, results_full, db_path=db_path, parquet_dir=tmp_path)
        assert db_path.exists()

    def test_returns_artifact_paths(self, artifacts, tmp_path) -> None:  # type: ignore[no-untyped-def]
        assert artifacts["duckdb"] == str(tmp_path / DB_FILENAME)
        assert artifacts["resultados_atribuicao"] == str(tmp_path / RESULTADOS_PARQUET)
        assert artifacts["fato_jornadas"] == str(tmp_path / FATO_JOURNEYS_PARQUET)

    def test_all_three_tables_populated(self, artifacts, tmp_path) -> None:  # type: ignore[no-untyped-def]
        con = duckdb.connect(str(tmp_path / DB_FILENAME), read_only=True)
        try:
            assert con.execute("SELECT COUNT(*) FROM fato_jornadas").fetchone()[0] == 3
            assert con.execute("SELECT COUNT(*) FROM dim_canais").fetchone()[0] == 6
            assert con.execute("SELECT COUNT(*) FROM resultados_atribuicao").fetchone()[0] == 6
        finally:
            con.close()

    def test_fato_jornadas_schema_types(self, artifacts, tmp_path) -> None:  # type: ignore[no-untyped-def]
        con = duckdb.connect(str(tmp_path / DB_FILENAME), read_only=True)
        try:
            schema = {row[0]: row[1] for row in con.execute("DESCRIBE fato_jornadas").fetchall()}
        finally:
            con.close()
        assert schema["journey_id"] == "VARCHAR"
        assert schema["channel_path"] == "VARCHAR[]"
        assert schema["path_length"] == "INTEGER"
        assert schema["converted"] == "BOOLEAN"
        assert schema["transaction_revenue"] == "DOUBLE"
        assert schema["first_visit_date"] == "DATE"

    def test_channel_path_stored_as_list(self, artifacts, tmp_path) -> None:  # type: ignore[no-untyped-def]
        con = duckdb.connect(str(tmp_path / DB_FILENAME), read_only=True)
        try:
            row = con.execute(
                "SELECT channel_path FROM fato_jornadas WHERE visitor_id = 'V1'"
            ).fetchone()
        finally:
            con.close()
        assert list(row[0]) == ["Organic Search", "Social", "Paid Search"]

    def test_resultados_has_credit_and_revenue_columns(self, artifacts, tmp_path) -> None:  # type: ignore[no-untyped-def]
        con = duckdb.connect(str(tmp_path / DB_FILENAME), read_only=True)
        try:
            schema = {
                row[0]: row[1] for row in con.execute("DESCRIBE resultados_atribuicao").fetchall()
            }
            row = con.execute(
                "SELECT first_click_credit, first_click_revenue FROM resultados_atribuicao LIMIT 1"
            ).fetchone()
        finally:
            con.close()
        for col in (
            "first_click_credit",
            "last_click_credit",
            "linear_credit",
            "markov_credit",
            "shapley_credit",
            "first_click_revenue",
            "last_click_revenue",
            "linear_revenue",
            "markov_revenue",
            "shapley_revenue",
        ):
            assert col in schema
        assert all(isinstance(v, float) for v in row)


class TestIdempotency:
    def test_rerun_does_not_duplicate(self, journeys, results_full, tmp_path) -> None:  # type: ignore[no-untyped-def]
        db_path = tmp_path / DB_FILENAME
        kwargs = {"db_path": db_path, "parquet_dir": tmp_path}
        persist(journeys, results_full, **kwargs)
        persist(journeys, results_full, **kwargs)
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            assert con.execute("SELECT COUNT(*) FROM fato_jornadas").fetchone()[0] == 3
            assert con.execute("SELECT COUNT(*) FROM resultados_atribuicao").fetchone()[0] == 6
        finally:
            con.close()


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
    def test_writes_under_data_dir(self, journeys, results_full, tmp_path) -> None:  # type: ignore[no-untyped-def]
        artifacts = persist_all(journeys, results_full, str(tmp_path))
        assert (tmp_path / DB_FILENAME).exists()
        assert (tmp_path / RESULTADOS_PARQUET).exists()
        assert artifacts["duckdb"].endswith(DB_FILENAME)
