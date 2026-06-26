"""Application configuration loaded from environment variables.

Settings are immutable and dependency-injected (``Settings.from_env`` accepts an
optional ``env`` mapping) so tests never touch the real process environment.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date


class ConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""


def _require(env: Mapping[str, str], key: str) -> str:
    try:
        value = env[key]
    except KeyError as exc:
        raise ConfigError(f"Missing required environment variable: {key}") from exc
    stripped = value.strip()
    if not stripped:
        raise ConfigError(f"Environment variable {key} is empty")
    return stripped


def _parse_date(value: str, key: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be ISO-8601 (YYYY-MM-DD), got: {value!r}") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable runtime settings for the attribution pipeline."""

    gcp_project_id: str
    google_application_credentials: str
    bq_dataset: str
    bq_start_date: date
    bq_end_date: date
    data_dir: str
    log_level: str
    max_retries: int

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        """Build settings from environment variables.

        Args:
            env: Optional environment mapping (defaults to ``os.environ``).
                Injecting a dict keeps the configuration trivially testable.
        """
        source = env if env is not None else os.environ

        gcp_project_id = _require(source, "GCP_PROJECT_ID")
        credentials = _require(source, "GOOGLE_APPLICATION_CREDENTIALS")
        default_dataset = "bigquery-public-data.google_analytics_sample"
        bq_dataset = source.get("BQ_DATASET", default_dataset).strip()
        if not bq_dataset:
            raise ConfigError("BQ_DATASET must not be empty")

        start_date = _parse_date(_require(source, "BQ_START_DATE"), "BQ_START_DATE")
        end_date = _parse_date(_require(source, "BQ_END_DATE"), "BQ_END_DATE")
        if end_date < start_date:
            raise ConfigError("BQ_END_DATE must not be earlier than BQ_START_DATE")

        data_dir = source.get("DATA_DIR", "/app/data").strip() or "/app/data"
        log_level = source.get("LOG_LEVEL", "INFO").strip().upper() or "INFO"
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigError(f"Unsupported LOG_LEVEL: {log_level!r}")

        max_retries_raw = source.get("BQ_MAX_RETRIES", "3").strip()
        try:
            max_retries = int(max_retries_raw)
        except ValueError as exc:
            msg = f"BQ_MAX_RETRIES must be an integer, got: {max_retries_raw!r}"
            raise ConfigError(msg) from exc
        if max_retries < 1:
            raise ConfigError("BQ_MAX_RETRIES must be >= 1")

        return cls(
            gcp_project_id=gcp_project_id,
            google_application_credentials=credentials,
            bq_dataset=bq_dataset,
            bq_start_date=start_date,
            bq_end_date=end_date,
            data_dir=data_dir,
            log_level=log_level,
            max_retries=max_retries,
        )
