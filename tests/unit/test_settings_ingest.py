"""The ingest daemon's environment (REQ-WP-076, REQ-WP-078)."""

# @trace: REQ-WP-076
# @trace: REQ-WP-078

import pytest

from channelflow.pipeline.ingest_main import (
    MAX_SILENCE_SECONDS,
    MissingConfiguration,
    ingest_settings_from_env,
)

BASE = {
    "CHANNELFLOW_INGEST_SYMBOLS": "BTCUSDT",
    "CHANNELFLOW_ARCHIVE_URI": "s3://bucket/raw",
    "CHANNELFLOW_INGEST_TIMEFRAME_NS": "60000000000",
}


class TestIngestSettingsEnv:
    """The ingest settings read their environment and refuse what cannot be meant."""

    @pytest.mark.trace("REQ-WP-078")
    def test_an_unset_silence_limit_leaves_the_policys_own(self):
        assert ingest_settings_from_env(environ=dict(BASE)).max_silence_ns is None

    @pytest.mark.trace("REQ-WP-078")
    def test_a_blank_silence_limit_is_unset_not_an_error(self):
        """Compose forwards `${CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS:-}`, which is the
        empty string whenever nobody set it -- the normal case."""
        settings = ingest_settings_from_env(environ={**BASE, MAX_SILENCE_SECONDS: ""})

        assert settings.max_silence_ns is None

    @pytest.mark.trace("REQ-WP-078")
    @pytest.mark.parametrize(
        ("text", "nanoseconds"), [("90", 90_000_000_000), ("1.5", 1_500_000_000)]
    )
    def test_a_silence_limit_is_seconds_converted_to_nanoseconds(self, text, nanoseconds):
        settings = ingest_settings_from_env(environ={**BASE, MAX_SILENCE_SECONDS: text})

        assert settings.max_silence_ns == nanoseconds

    @pytest.mark.trace("REQ-WP-078")
    @pytest.mark.parametrize("text", ["0", "-1", "abc", "nan", "inf"])
    def test_a_silence_limit_that_cannot_be_meant_is_refused_naming_the_variable(self, text):
        with pytest.raises(MissingConfiguration, match=MAX_SILENCE_SECONDS):
            ingest_settings_from_env(environ={**BASE, MAX_SILENCE_SECONDS: text})

    @pytest.mark.trace("REQ-WP-078")
    def test_the_retired_multiplier_is_refused_and_not_quietly_ignored(self):
        """It multiplied a quantity that meant something else on each venue. A deployment
        that still sets it would otherwise believe it was being honoured."""
        with pytest.raises(MissingConfiguration, match=MAX_SILENCE_SECONDS):
            ingest_settings_from_env(
                environ={**BASE, "CHANNELFLOW_SILENCE_WINDOW_MULTIPLIER": "1.5"}
            )

    @pytest.mark.trace("REQ-WP-078")
    def test_a_blank_retired_multiplier_is_fine(self):
        settings = ingest_settings_from_env(
            environ={**BASE, "CHANNELFLOW_SILENCE_WINDOW_MULTIPLIER": ""}
        )

        assert settings.max_silence_ns is None
