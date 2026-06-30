"""Tests for :mod:`src.main`."""

from __future__ import annotations

from typing import Any

import pandas as pd
from src.main import PENDING_PHASES, PipelineResult, main, run_pipeline


def _fake_persister(
    journeys: pd.DataFrame, results_full: pd.DataFrame, data_dir: str
) -> dict[str, str]:
    return {
        "postgres": "postgresql://localhost:5433/marketing_db",
        "resultados_atribuicao": f"{data_dir}/resultados_atribuicao.parquet",
        "fato_jornadas": f"{data_dir}/fato_jornadas.parquet",
    }


class TestRunPipeline:
    def test_runs_all_phases_and_persists(
        self,
        settings,
        fake_ingester,  # type: ignore[no-untyped-def]
    ) -> None:
        result = run_pipeline(settings, ingester=fake_ingester, persister=_fake_persister)
        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert result.exit_code == 0
        assert result.phases_run == ["ingestion", "preprocessing", "attribution", "persistence"]
        assert result.phases_pending == list(PENDING_PHASES)
        assert result.sessions_rows == 2
        assert result.journeys_rows == 2
        assert result.conversions == 1
        assert result.stats["unique_channels"] == 2.0
        assert "postgres" in result.artifacts
        assert "resultados_atribuicao" in result.artifacts
        assert "fato_jornadas" in result.artifacts
        assert "duckdb" not in result.artifacts

    def test_message_reports_outputs_ready(
        self,
        settings,
        fake_ingester,  # type: ignore[no-untyped-def]
    ) -> None:
        result = run_pipeline(settings, ingester=fake_ingester, persister=_fake_persister)
        assert "PostgreSQL" in result.message
        assert "Grafana" in result.message

    def test_default_persister_used_when_not_injected(
        self,
        settings,
        fake_ingester,
        monkeypatch,  # type: ignore[no-untyped-def]
    ) -> None:
        captured: dict[str, Any] = {}
        original = _fake_persister

        def spy(
            journeys: pd.DataFrame, results_full: pd.DataFrame, data_dir: str
        ) -> dict[str, str]:
            captured["called"] = True
            return original(journeys, results_full, data_dir)

        import src.main as main_mod

        monkeypatch.setattr(main_mod, "persist_all", spy)
        result = run_pipeline(settings, ingester=fake_ingester)
        assert captured.get("called") is True
        assert result.phases_run[-1] == "persistence"


class TestMainEntryPoint:
    def test_invalid_config_returns_exit_code_2(
        self,
        monkeypatch,
        capsys,  # type: ignore[no-untyped-def]
    ) -> None:
        monkeypatch.setenv("GCP_PROJECT_ID", "")
        for key in ("GOOGLE_APPLICATION_CREDENTIALS", "BQ_START_DATE", "BQ_END_DATE"):
            monkeypatch.delenv(key, raising=False)
        code = main([])
        assert code == 2
        captured = capsys.readouterr()
        assert "Configuration error" in captured.err

    def test_dry_run_returns_zero(self, isolated_env) -> None:  # type: ignore[no-untyped-def]
        assert main(["--dry-run"]) == 0

    def test_full_run_with_injected_collaborators(
        self,
        isolated_env,
        fake_ingester,
        monkeypatch,  # type: ignore[no-untyped-def]
    ) -> None:
        import src.main as main_mod

        monkeypatch.setattr(main_mod, "default_ingester", lambda s: fake_ingester)
        monkeypatch.setattr(main_mod, "persist_all", _fake_persister)
        assert main([]) == 0

    def test_pipeline_failure_is_graceful(
        self,
        isolated_env,
        monkeypatch,
        capsys,  # type: ignore[no-untyped-def]
    ) -> None:
        import src.main as main_mod

        class _Boom:
            def run(self) -> pd.DataFrame:
                raise RuntimeError("credentials missing")

        monkeypatch.setattr(main_mod, "default_ingester", lambda s: _Boom())
        code = main([])
        assert code == 1
        assert "Pipeline failed" in capsys.readouterr().err
