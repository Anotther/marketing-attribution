"""Structured logging setup for the attribution pipeline.

The PRD (section 6 - Observability NFRs) requires logs with timestamp, level
and module. This module configures the root logger once and exposes a context
manager that times a logical phase, satisfying the "metrics of execution"
requirement (time per phase).
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

_CONFIGURED = False


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure the root logger with a structured single-line format.

    Idempotent: calling it multiple times re-configures the level safely without
    duplicating handlers.
    """
    global _CONFIGURED
    root = logging.getLogger()

    if not _CONFIGURED:
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        root.addHandler(handler)
        _CONFIGURED = True

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(numeric_level)
    for h in root.handlers:
        h.setLevel(numeric_level)

    logging.captureWarnings(True)
    return logging.getLogger("attribution")


@contextmanager
def timed_phase(logger: logging.Logger, name: str, **context: Any) -> Iterator[dict[str, Any]]:
    """Context manager that logs the wall-clock duration of a pipeline phase.

    Yields a metrics dict that callers may populate with phase-specific counts
    (e.g. rows processed); those metrics are emitted alongside the duration on
    exit.
    """
    metrics: dict[str, Any] = dict(context)
    logger.info("phase.start name=%s", name, extra={"phase": name, "event": "start"})
    start = time.perf_counter()
    try:
        yield metrics
    except Exception:
        elapsed = time.perf_counter() - start
        logger.exception(
            "phase.error name=%s duration_seconds=%.3f",
            name,
            elapsed,
            extra={"phase": name, "event": "error", "duration_seconds": round(elapsed, 3)},
        )
        raise
    else:
        elapsed = time.perf_counter() - start
        metrics["duration_seconds"] = round(elapsed, 3)
        logger.info(
            "phase.complete name=%s duration_seconds=%.3f %s",
            name,
            elapsed,
            " ".join(f"{k}={v}" for k, v in metrics.items() if k != "duration_seconds"),
            extra={"phase": name, "event": "complete", **metrics},
        )
