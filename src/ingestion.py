"""BigQuery ingestion and raw-session cleaning (PRD Module 1, RF1.1-RF1.4).

Design goals:
- **Mockable I/O** (risk R1): the BigQuery client is injected, so the module is
  fully testable without GCP credentials or network access.
- **Pure cleaning** (RF1.3): ``clean_sessions`` is a side-effect-free transform
  separated from the network call.
- **Resilience** (NFR): the query is retried with exponential backoff.
- **Schema guard** (risk R4): the expected GA columns are validated up front.

GA stores ``transactionRevenue`` in micros, so values are divided by 1e6 to
obtain dollars. ``date`` arrives as ``YYYYMMDD`` and is parsed to ``datetime64``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence
from datetime import date
from typing import Any, Protocol

import pandas as pd

logger = logging.getLogger("attribution.ingestion")

#: Canonical raw columns extracted from the GA sample (RF1.2).
EXPECTED_RAW_COLUMNS: tuple[str, ...] = (
    "fullVisitorId",
    "channelGrouping",
    "visitNumber",
    "date",
    "transactions",
    "transactionRevenue",
)

#: Revenue is stored by GA in millionths of a unit (micros).
REVENUE_MICROS_DIVISOR = 1_000_000


class SchemaError(ValueError):
    """Raised when the BigQuery result does not match the expected GA schema."""


class IngestionError(RuntimeError):
    """Raised when BigQuery extraction exhausts all retries."""


class BigQueryClient(Protocol):
    """Structural type for any object usable as a BigQuery client in tests."""

    def query(self, query: str, job_config: Any = ...) -> Any: ...


def build_extraction_query(dataset: str) -> str:
    """Build the parameterised extraction SQL for a sharded GA dataset (RF1.2).

    The dataset is interpolated into the table reference while the date window
    is bound via query parameters (``@start_date`` / ``@end_date``) to avoid
    string injection and let BigQuery cache the plan.
    """
    return f"""
SELECT
    fullVisitorId,
    channelGrouping,
    visitNumber,
    date,
    totals.transactions        AS transactions,
    totals.transactionRevenue  AS transactionRevenue
FROM `{dataset}.ga_sessions_*`
WHERE _TABLE_SUFFIX BETWEEN @start_date AND @end_date
""".strip()


def build_query_parameters(start: date, end: date) -> list[Any]:
    """Build the BigQuery scalar query parameters for the date window (RF1.4)."""
    from google.cloud import bigquery  # local import: keeps test imports light

    return [
        bigquery.ScalarQueryParameter("start_date", "STRING", start.strftime("%Y%m%d")),
        bigquery.ScalarQueryParameter("end_date", "STRING", end.strftime("%Y%m%d")),
    ]


def _validate_schema(df: pd.DataFrame) -> None:
    missing = [c for c in EXPECTED_RAW_COLUMNS if c not in df.columns]
    if missing:
        raise SchemaError(f"BigQuery result missing expected columns: {missing}")


def clean_sessions(raw: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalise raw GA sessions into a typed dataframe (RF1.3).

    - drops rows with a null visitor id and logs the discard count;
    - parses the ``YYYYMMDD`` ``date`` string into a ``datetime64[ns]``;
    - coerces transactions to integer units (filling nulls with 0);
    - converts ``transactionRevenue`` from micros to dollars (÷1e6).

    The input is not mutated; a normalised copy is returned.
    """
    _validate_schema(raw)
    df = raw.copy()

    before = len(df)
    df = df.dropna(subset=["fullVisitorId"])
    discarded = before - len(df)
    if discarded:
        logger.warning("ingestion.discarded rows=%d reason=null_visitor", discarded)

    df["fullVisitorId"] = df["fullVisitorId"].astype(str)
    df["channelGrouping"] = df["channelGrouping"].astype(str)
    df["visitNumber"] = pd.to_numeric(df["visitNumber"], errors="coerce").fillna(0).astype("int64")
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")

    transactions = pd.to_numeric(df["transactions"], errors="coerce").fillna(0).astype("int64")
    df["transactions"] = transactions

    revenue_micros = pd.to_numeric(df["transactionRevenue"], errors="coerce").fillna(0.0)
    df["transactionRevenue"] = (revenue_micros / REVENUE_MICROS_DIVISOR).astype("float64")

    bad_dates = int(df["date"].isna().sum())
    if bad_dates:
        logger.warning("ingestion.discarded rows=%d reason=bad_date", bad_dates)
        df = df[df["date"].notna()]

    logger.info(
        "ingestion.clean rows_in=%d rows_out=%d discarded=%d",
        before,
        len(df),
        discarded + bad_dates,
    )
    return df[list(EXPECTED_RAW_COLUMNS)]


class BigQueryIngester:
    """Extracts and cleans GA sessions from BigQuery with retry (RF1.1, NFR)."""

    def __init__(
        self,
        client: BigQueryClient,
        dataset: str,
        start: date,
        end: date,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
        backoff_base: float = 2.0,
    ) -> None:
        self._client = client
        self._dataset = dataset
        self._start = start
        self._end = end
        self._max_retries = max_retries
        self._sleep = sleep
        self._backoff_base = backoff_base

    @classmethod
    def from_settings(cls, settings: Any, client: BigQueryClient | None = None) -> BigQueryIngester:
        """Construct an ingester from :class:`Settings`, creating the client if absent."""
        if client is None:
            from google.cloud import bigquery

            client = bigquery.Client(project=settings.gcp_project_id)
        return cls(
            client=client,
            dataset=settings.bq_dataset,
            start=settings.bq_start_date,
            end=settings.bq_end_date,
            max_retries=settings.max_retries,
        )

    def _run_query(self) -> pd.DataFrame:
        from google.cloud import bigquery

        query = build_extraction_query(self._dataset)
        params = build_query_parameters(self._start, self._end)
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        job = self._client.query(query, job_config=job_config)
        return job.to_dataframe()

    def _extract_with_retry(self) -> pd.DataFrame:
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                logger.info("ingestion.query attempt=%d/%d", attempt + 1, self._max_retries)
                return self._run_query()
            except Exception as exc:  # noqa: BLE001 - surfaced via IngestionError
                last_error = exc
                if attempt + 1 < self._max_retries:
                    delay = self._backoff_base**attempt
                    logger.warning(
                        "ingestion.retry attempt=%d delay=%.1fs error=%s",
                        attempt + 1,
                        delay,
                        exc,
                    )
                    self._sleep(delay)
        msg = f"BigQuery extraction failed after {self._max_retries} attempts"
        raise IngestionError(msg) from last_error

    def run(self) -> pd.DataFrame:
        """Extract raw sessions from BigQuery and return the cleaned dataframe."""
        raw = self._extract_with_retry()
        logger.info("ingestion.raw rows=%d", len(raw))
        return clean_sessions(raw)


#: Structural type accepted by the pipeline for the ingestion phase.
class Ingester(Protocol):
    def run(self) -> pd.DataFrame: ...


def default_ingester(settings: Any) -> Ingester:
    """Default factory used by the CLI; constructs a real BigQuery-backed ingester."""
    return BigQueryIngester.from_settings(settings)


__all__: Sequence[str] = (
    "EXPECTED_RAW_COLUMNS",
    "REVENUE_MICROS_DIVISOR",
    "BigQueryIngester",
    "BigQueryClient",
    "Ingester",
    "IngestionError",
    "SchemaError",
    "build_extraction_query",
    "build_query_parameters",
    "clean_sessions",
    "default_ingester",
)
