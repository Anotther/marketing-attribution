"""Persistence layer: DuckDB analytics store + Parquet exports (PRD RF4.1-RF4.6).

Creates ``attribution_data.duckdb`` in the data directory with three tables
(``fato_jornadas``, ``dim_canais``, ``resultados_atribuicao``) matching PRD
section 9, and exports flat Parquet files for Power BI / pandas consumption.

Idempotency (PRD RF4.6) is enforced with ``CREATE OR REPLACE TABLE`` followed by
fresh inserts, so re-running the pipeline reproduces identical state. The
DuckDB connection is injectable so the layer is fully testable with an
in-memory database.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from src.preprocessing import build_channel_dimension

logger = logging.getLogger("attribution.persistence")

DB_FILENAME = "attribution_data.duckdb"
RESULTADOS_PARQUET = "resultados_atribuicao.parquet"
FATO_JOURNEYS_PARQUET = "fato_jornadas.parquet"

_FATO_DDL = """
CREATE OR REPLACE TABLE fato_jornadas (
    journey_id          VARCHAR PRIMARY KEY,
    visitor_id          VARCHAR,
    channel_path        VARCHAR[],
    path_length         INTEGER,
    converted           BOOLEAN,
    transaction_revenue DOUBLE,
    first_visit_date    DATE,
    last_visit_date     DATE
)
"""

_DIM_DDL = """
CREATE OR REPLACE TABLE dim_canais (
    channel_name        VARCHAR PRIMARY KEY,
    total_sessions      INTEGER,
    total_conversions   INTEGER,
    total_revenue       DOUBLE,
    avg_position        DOUBLE,
    conversion_rate     DOUBLE
)
"""

_RESULTADOS_DDL = """
CREATE OR REPLACE TABLE resultados_atribuicao (
    channel_name          VARCHAR PRIMARY KEY,
    first_click_credit    DOUBLE,
    last_click_credit     DOUBLE,
    linear_credit         DOUBLE,
    markov_credit         DOUBLE,
    shapley_credit        DOUBLE,
    first_click_revenue   DOUBLE,
    last_click_revenue    DOUBLE,
    linear_revenue        DOUBLE,
    markov_revenue        DOUBLE,
    shapley_revenue       DOUBLE
)
"""

_DDL: tuple[str, ...] = (_FATO_DDL, _DIM_DDL, _RESULTADOS_DDL)

_FATO_INSERT = """
INSERT INTO fato_jornadas
SELECT
    journey_id,
    visitor_id,
    channel_path,
    CAST(path_length AS INTEGER),
    CAST(converted AS BOOLEAN),
    CAST(transaction_revenue AS DOUBLE),
    CAST(first_visit_date AS DATE),
    CAST(last_visit_date AS DATE)
FROM jrn
"""

_DIM_INSERT = """
INSERT INTO dim_canais
SELECT
    channel_name,
    CAST(total_sessions AS INTEGER),
    CAST(total_conversions AS INTEGER),
    CAST(total_revenue AS DOUBLE),
    CAST(avg_position AS DOUBLE),
    CAST(conversion_rate AS DOUBLE)
FROM dim
"""

_RESULTADOS_INSERT = """
INSERT INTO resultados_atribuicao
SELECT
    channel AS channel_name,
    first_click_credit, last_click_credit, linear_credit,
    markov_credit, shapley_credit,
    first_click_revenue, last_click_revenue, linear_revenue,
    markov_revenue, shapley_revenue
FROM res
"""


def _create_tables(con: Any) -> None:
    for statement in _DDL:
        con.execute(statement)


def _insert_fato_journeys(con: Any, journeys: pd.DataFrame) -> None:
    con.register("jrn", journeys)
    con.execute(_FATO_INSERT)


def _insert_dim_canais(con: Any, dimension: pd.DataFrame) -> None:
    con.register("dim", dimension)
    con.execute(_DIM_INSERT)


def _insert_resultados(con: Any, results_full: pd.DataFrame) -> None:
    con.register("res", results_full)
    con.execute(_RESULTADOS_INSERT)


def _export_parquet(
    journeys: pd.DataFrame, results_full: pd.DataFrame, parquet_dir: Path
) -> dict[str, str]:
    resultados_path = parquet_dir / RESULTADOS_PARQUET
    fato_path = parquet_dir / FATO_JOURNEYS_PARQUET
    results_full.to_parquet(resultados_path, index=False)
    journeys.to_parquet(fato_path, index=False)
    logger.info("persistence.parquet resultados=%s journeys=%s", resultados_path, fato_path)
    return {
        "resultados_atribuicao": str(resultados_path),
        "fato_jornadas": str(fato_path),
    }


def persist(
    journeys: pd.DataFrame,
    results_full: pd.DataFrame,
    *,
    db_path: Path,
    parquet_dir: Path,
    connection: Any = None,
) -> dict[str, str]:
    """Write journeys + results to DuckDB and Parquet (PRD RF4.1-RF4.6).

    Args:
        journeys: journeys dataframe (``fato_jornadas`` shape).
        results_full: per-channel credit + revenue frame from
            :func:`src.models.attribute_full`.
        db_path: location of the DuckDB file (created if absent).
        parquet_dir: directory for the Parquet exports.
        connection: optional DuckDB connection (in-memory in tests). When
            omitted a file connection at ``db_path`` is opened and closed here.
    """
    owns_connection = connection is None
    con = connection if connection is not None else _connect(db_path)
    try:
        _create_tables(con)
        _insert_fato_journeys(con, journeys)
        _insert_dim_canais(con, build_channel_dimension(journeys))
        _insert_resultados(con, results_full)
        logger.info(
            "persistence.duckdb path=%s journeys=%d channels=%d",
            db_path,
            len(journeys),
            len(results_full),
        )
    finally:
        if owns_connection:
            con.close()

    parquet_dir.mkdir(parents=True, exist_ok=True)
    artifacts = _export_parquet(journeys, results_full, parquet_dir)
    artifacts["duckdb"] = str(db_path)
    return artifacts


def _connect(db_path: Path) -> Any:
    import duckdb

    return duckdb.connect(str(db_path))


def persist_all(
    journeys: pd.DataFrame, results_full: pd.DataFrame, data_dir: str
) -> dict[str, str]:
    """Default persister used by the pipeline: writes under ``data_dir``."""
    base = Path(data_dir)
    base.mkdir(parents=True, exist_ok=True)
    return persist(
        journeys,
        results_full,
        db_path=base / DB_FILENAME,
        parquet_dir=base,
    )
