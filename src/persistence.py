"""Persistence layer: PostgreSQL analytics store + Parquet exports (PRD RF4.1-RF4.6).

Writes to PostgreSQL using SQLAlchemy, replacing the original DuckDB implementation.
Exports flat Parquet files for Power BI consumption.

Idempotency (PRD RF4.6) is enforced with ``if_exists="replace"`` during Pandas to_sql,
so re-running the pipeline reproduces identical state.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, create_engine

from src.preprocessing import build_channel_dimension

logger = logging.getLogger("attribution.persistence")

RESULTADOS_PARQUET = "resultados_atribuicao.parquet"
FATO_JOURNEYS_PARQUET = "fato_jornadas.parquet"


def _insert_fato_journeys(engine: Engine, journeys: pd.DataFrame) -> None:
    df = journeys.copy()
    if "channel_path" in df.columns:
        df["channel_path"] = df["channel_path"].apply(
            lambda x: ",".join(x) if isinstance(x, list) else x
        )
    df.to_sql("fato_jornadas", engine, if_exists="replace", index=False)


def _insert_dim_canais(engine: Engine, dimension: pd.DataFrame) -> None:
    dimension.to_sql("dim_canais", engine, if_exists="replace", index=False)


def _insert_resultados(engine: Engine, results_full: pd.DataFrame) -> None:
    results_full.to_sql("resultados_atribuicao", engine, if_exists="replace", index=False)


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
    db_url: str,
    parquet_dir: Path,
) -> dict[str, str]:
    """Write journeys + results to PostgreSQL and Parquet (PRD RF4.1-RF4.6).

    Args:
        journeys: journeys dataframe (``fato_jornadas`` shape).
        results_full: per-channel credit + revenue frame from
            :func:`src.models.attribute_full`.
        db_url: SQLAlchemy database URL (e.g., postgresql://...).
        parquet_dir: directory for the Parquet exports.
    """
    engine = create_engine(db_url)
    
    _insert_fato_journeys(engine, journeys)
    _insert_dim_canais(engine, build_channel_dimension(journeys))
    _insert_resultados(engine, results_full)
    
    # Hide password in logs if present
    safe_url = db_url.split("@")[-1] if "@" in db_url else db_url
    logger.info(
        "persistence.postgres target=%s journeys=%d channels=%d",
        safe_url,
        len(journeys),
        len(results_full),
    )

    parquet_dir.mkdir(parents=True, exist_ok=True)
    artifacts = _export_parquet(journeys, results_full, parquet_dir)
    artifacts["postgres"] = db_url
    return artifacts


def persist_all(
    journeys: pd.DataFrame, results_full: pd.DataFrame, data_dir: str
) -> dict[str, str]:
    """Default persister used by the pipeline: writes under ``data_dir`` and connects to DB."""
    base = Path(data_dir)
    base.mkdir(parents=True, exist_ok=True)
    db_url = os.getenv("DATABASE_URL", "postgresql://user:pass@postgres-dev:5432/marketing_db")
    return persist(
        journeys,
        results_full,
        db_url=db_url,
        parquet_dir=base,
    )
