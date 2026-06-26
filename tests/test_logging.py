"""Tests for :mod:`src.logging_setup`."""

from __future__ import annotations

import logging

import pytest
from src.logging_setup import setup_logging, timed_phase


class TestSetupLogging:
    def test_returns_attribution_logger(self) -> None:
        log = setup_logging("INFO")
        assert log.name == "attribution"

    def test_sets_level(self) -> None:
        setup_logging("DEBUG")
        assert logging.getLogger().level == logging.DEBUG

    def test_idempotent_no_duplicate_handlers(self) -> None:
        setup_logging("INFO")
        before = len(logging.getLogger().handlers)
        setup_logging("WARNING")
        after = len(logging.getLogger().handlers)
        assert after == before


class TestTimedPhase:
    def test_complete_emits_metrics(self, caplog: pytest.LogCaptureFixture) -> None:
        log = setup_logging("INFO")
        caplog.set_level(logging.INFO, logger="attribution")
        with timed_phase(log, "ingestion", rows=1000) as metrics:
            metrics["processed"] = 999

        events = [
            r.message
            for r in caplog.records
            if r.name == "attribution.main" or "phase" in r.message
        ]
        assert any("phase.start" in m and "ingestion" in m for m in events)
        assert any("phase.complete" in m and "ingestion" in m for m in events)

    def test_error_propagates_and_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        log = setup_logging("ERROR")
        caplog.set_level(logging.ERROR, logger="attribution")
        with pytest.raises(RuntimeError), timed_phase(log, "boom"):
            raise RuntimeError("phase failed")
        assert any("phase.error" in r.message for r in caplog.records)
