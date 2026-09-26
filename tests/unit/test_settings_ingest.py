"""Tests for ingest daemon env vars (REQ-WP-076)."""

# @trace: REQ-WP-076

import pytest

from channelflow.pipeline.ingest_main import (
    DEFAULT_SILENCE_WINDOW_MULTIPLIER,
    SILENCE_WINDOW_MULTIPLIER,
    MissingConfiguration,
    ingest_settings_from_env,
)


class TestIngestSettingsEnv:
    """The ingest settings read their env vars and refuse invalid values."""

    @pytest.mark.trace("REQ-WP-076")
    def test_silence_window_multiplier_default(self):
        """Unset variable yields the default multiplier."""
        settings = ingest_settings_from_env(
            environ={
                "CHANNELFLOW_INGEST_SYMBOLS": "BTCUSDT",
                "CHANNELFLOW_ARCHIVE_URI": "s3://bucket/raw",
                "CHANNELFLOW_INGEST_TIMEFRAME_NS": "60000000000",
            }
        )
        assert settings.silence_window_multiplier == DEFAULT_SILENCE_WINDOW_MULTIPLIER

    @pytest.mark.trace("REQ-WP-076")
    def test_silence_window_multiplier_custom(self):
        """Custom value is parsed as float."""
        settings = ingest_settings_from_env(
            environ={
                "CHANNELFLOW_INGEST_SYMBOLS": "BTCUSDT",
                "CHANNELFLOW_ARCHIVE_URI": "s3://bucket/raw",
                "CHANNELFLOW_INGEST_TIMEFRAME_NS": "60000000000",
                SILENCE_WINDOW_MULTIPLIER: "1.5",
            }
        )
        assert settings.silence_window_multiplier == 1.5

    @pytest.mark.trace("REQ-WP-076")
    def test_silence_window_multiplier_refuses_zero(self):
        """Zero or negative multiplier is rejected."""
        with pytest.raises(MissingConfiguration, match=SILENCE_WINDOW_MULTIPLIER):
            ingest_settings_from_env(
                environ={
                    "CHANNELFLOW_INGEST_SYMBOLS": "BTCUSDT",
                    "CHANNELFLOW_ARCHIVE_URI": "s3://bucket/raw",
                    "CHANNELFLOW_INGEST_TIMEFRAME_NS": "60000000000",
                    SILENCE_WINDOW_MULTIPLIER: "0",
                }
            )

    @pytest.mark.trace("REQ-WP-076")
    def test_silence_window_multiplier_refuses_negative(self):
        with pytest.raises(MissingConfiguration, match=SILENCE_WINDOW_MULTIPLIER):
            ingest_settings_from_env(
                environ={
                    "CHANNELFLOW_INGEST_SYMBOLS": "BTCUSDT",
                    "CHANNELFLOW_ARCHIVE_URI": "s3://bucket/raw",
                    "CHANNELFLOW_INGEST_TIMEFRAME_NS": "60000000000",
                    SILENCE_WINDOW_MULTIPLIER: "-1",
                }
            )
