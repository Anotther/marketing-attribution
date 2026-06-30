"""Tests for :mod:`src.config`."""

from __future__ import annotations

from datetime import date

import pytest
from src.config import ConfigError, Settings


class TestSettingsFromEnv:
    def test_loads_required_and_defaults(self, base_env: dict[str, str]) -> None:
        settings = Settings.from_env(base_env)
        assert settings.gcp_project_id == "test-project"
        assert settings.google_application_credentials == "credentials/gcp-sa.json"
        assert settings.bq_dataset == "bigquery-public-data.google_analytics_sample"
        assert settings.bq_start_date == date(2016, 8, 1)
        assert settings.bq_end_date == date(2017, 8, 1)
        assert settings.data_dir == "data"
        assert settings.log_level == "INFO"
        assert settings.max_retries == 3

    def test_uses_overrides(self, base_env: dict[str, str]) -> None:
        base_env.update(
            {
                "BQ_DATASET": "my-project.my_dataset",
                "DATA_DIR": "/tmp/out",
                "LOG_LEVEL": "debug",
                "BQ_MAX_RETRIES": "5",
            }
        )
        settings = Settings.from_env(base_env)
        assert settings.bq_dataset == "my-project.my_dataset"
        assert settings.data_dir == "/tmp/out"
        assert settings.log_level == "DEBUG"
        assert settings.max_retries == 5

    @pytest.mark.parametrize(
        "missing",
        ["GCP_PROJECT_ID", "GOOGLE_APPLICATION_CREDENTIALS", "BQ_START_DATE", "BQ_END_DATE"],
    )
    def test_missing_required_raises(self, base_env: dict[str, str], missing: str) -> None:
        del base_env[missing]
        with pytest.raises(ConfigError, match=missing):
            Settings.from_env(base_env)

    def test_empty_required_raises(self, base_env: dict[str, str]) -> None:
        base_env["GCP_PROJECT_ID"] = "   "
        with pytest.raises(ConfigError, match="GCP_PROJECT_ID"):
            Settings.from_env(base_env)

    def test_invalid_date_raises(self, base_env: dict[str, str]) -> None:
        base_env["BQ_START_DATE"] = "01-08-2016"
        with pytest.raises(ConfigError, match="ISO-8601"):
            Settings.from_env(base_env)

    def test_end_before_start_raises(self, base_env: dict[str, str]) -> None:
        base_env["BQ_START_DATE"] = "2017-08-01"
        base_env["BQ_END_DATE"] = "2016-08-01"
        with pytest.raises(ConfigError, match="BQ_END_DATE"):
            Settings.from_env(base_env)

    def test_invalid_log_level_raises(self, base_env: dict[str, str]) -> None:
        base_env["LOG_LEVEL"] = "VERBOSE"
        with pytest.raises(ConfigError, match="LOG_LEVEL"):
            Settings.from_env(base_env)

    def test_empty_bq_dataset_raises(self, base_env: dict[str, str]) -> None:
        base_env["BQ_DATASET"] = "   "
        with pytest.raises(ConfigError, match="BQ_DATASET"):
            Settings.from_env(base_env)

    @pytest.mark.parametrize("value", ["0", "-1", "abc"])
    def test_invalid_retries_raises(self, base_env: dict[str, str], value: str) -> None:
        base_env["BQ_MAX_RETRIES"] = value
        with pytest.raises(ConfigError, match="BQ_MAX_RETRIES"):
            Settings.from_env(base_env)

    def test_settings_are_immutable(self, base_env: dict[str, str]) -> None:
        settings = Settings.from_env(base_env)
        # frozen dataclass -> FrozenInstanceError (subclass of AttributeError)
        with pytest.raises(AttributeError):
            settings.gcp_project_id = "mutated"  # type: ignore[misc]
