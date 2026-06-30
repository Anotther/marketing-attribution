"""Pipeline entrypoint.

Orchestrates the attribution pipeline phases: ingestion -> preprocessing ->
attribution modelling -> persistence. The pipeline writes analytical tables to
PostgreSQL and exports Parquet files for BI/dashboard consumption.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.config import ConfigError, Settings
from src.ingestion import Ingester, default_ingester
from src.logging_setup import setup_logging, timed_phase
from src.models import attribute_full
from src.persistence import persist_all
from src.preprocessing import build_journeys, journey_stats

logger = logging.getLogger("attribution.main")

#: Phases still pending in later milestones.
PENDING_PHASES: tuple[str, ...] = ()


@dataclass(slots=True)
class PipelineResult:
    """Outcome of a pipeline run, used for process exit codes and tests."""

    success: bool
    phases_run: list[str] = field(default_factory=list)
    phases_pending: list[str] = field(default_factory=list)
    sessions_rows: int = 0
    journeys_rows: int = 0
    conversions: int = 0
    stats: dict[str, float] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    message: str = ""

    @property
    def exit_code(self) -> int:
        return 0 if self.success else 1


Persister = Callable[[pd.DataFrame, pd.DataFrame, str], dict[str, str]]


def run_pipeline(
    settings: Settings,
    *,
    ingester: Ingester | None = None,
    persister: Persister | None = None,
) -> PipelineResult:
    """Execute the full attribution pipeline against ``settings``.

    Phases implemented: ingestion (M2), preprocessing + attribution (M3),
    persistence (M4). ``ingester`` and ``persister`` are injectable so the
    orchestration is testable without GCP credentials or filesystem access.
    """
    logger.info(
        "pipeline.start project=%s dataset=%s window=%s..%s",
        settings.gcp_project_id,
        settings.bq_dataset,
        settings.bq_start_date.isoformat(),
        settings.bq_end_date.isoformat(),
        extra={
            "project": settings.gcp_project_id,
            "dataset": settings.bq_dataset,
            "start_date": settings.bq_start_date.isoformat(),
            "end_date": settings.bq_end_date.isoformat(),
        },
    )

    result = PipelineResult(success=True)
    context: dict[str, Any] = {}

    if ingester is None:
        ingester = default_ingester(settings)
    if persister is None:
        persister = persist_all

    with timed_phase(logger, "ingestion"):
        context["sessions"] = ingester.run()
    result.phases_run.append("ingestion")
    result.sessions_rows = int(len(context["sessions"]))

    with timed_phase(logger, "preprocessing"):
        context["journeys"] = build_journeys(context["sessions"])
        result.stats = journey_stats(context["journeys"])
    result.phases_run.append("preprocessing")
    result.journeys_rows = int(len(context["journeys"]))
    result.conversions = int(result.stats["total_conversions"])

    with timed_phase(logger, "attribution"):
        context["results_full"] = attribute_full(context["journeys"])
    result.phases_run.append("attribution")

    with timed_phase(logger, "persistence", data_dir=settings.data_dir):
        result.artifacts = persister(
            context["journeys"], context["results_full"], settings.data_dir
        )
    result.phases_run.append("persistence")

    logger.info(
        "pipeline.complete implemented=%d pending=%d journeys=%d conversions=%d artifacts=%d",
        len(result.phases_run),
        len(result.phases_pending),
        result.journeys_rows,
        result.conversions,
        len(result.artifacts),
    )
    result.message = "pipeline complete; PostgreSQL, Parquet and Grafana outputs ready"
    return result


#: Exit codes (meaningful, per PRD section 6 - Confiabilidade).
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 2
EXIT_RUNTIME_ERROR = 1


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="marketing-attribution",
        description="Omni-channel marketing attribution pipeline.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only load config and log; do not execute heavy phases.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Console entrypoint. Returns a meaningful process exit code."""
    args = _parse_args(argv)

    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        # Logging may not be configured yet; write to stderr regardless.
        setup_logging("ERROR")
        logger.error("config.invalid error=%s", exc, extra={"event": "config_error"})
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    setup_logging(settings.log_level)

    if args.dry_run:
        logger.info(
            "pipeline.dry-run window=%s..%s",
            settings.bq_start_date.isoformat(),
            settings.bq_end_date.isoformat(),
        )
        return EXIT_SUCCESS

    try:
        result = run_pipeline(settings)
    except Exception as exc:  # noqa: BLE001 - surface any failure as a clean exit
        logger.exception("pipeline.fatal error=%s", exc, extra={"event": "fatal"})
        print(f"Pipeline failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
