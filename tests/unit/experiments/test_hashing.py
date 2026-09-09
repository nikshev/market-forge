"""Hashing the config and the dataset (REQ-REPRO-001, PRD §0 item 13, §29.B)."""

from __future__ import annotations

import pytest

from channelflow.experiments import UnhashableConfig, config_hash, dataset_reference


@pytest.mark.trace("REQ-REPRO-001")
def test_a_config_hashes_the_same_however_it_was_written_down() -> None:
    """Key order is how a config was typed, not what it configures."""
    assert config_hash({"a": 1, "b": 2}) == config_hash({"b": 2, "a": 1})


@pytest.mark.trace("REQ-REPRO-001")
def test_a_config_that_differs_anywhere_hashes_differently() -> None:
    base = config_hash({"channel": {"lookback": 60, "quantiles": [0.1, 0.9]}})

    assert config_hash({"channel": {"lookback": 61, "quantiles": [0.1, 0.9]}}) != base
    assert config_hash({"channel": {"lookback": 60, "quantiles": [0.1, 0.95]}}) != base
    assert config_hash({"channel": {"lookback": 60}}) != base


@pytest.mark.trace("REQ-REPRO-001")
def test_a_quoted_flag_is_not_the_same_config_as_an_unquoted_one() -> None:
    """The failure a plain JSON dump would let through. `True` renders as `true`
    and collides with the string `"true"`, and a YAML config where a flag lost
    its quotes configures a different run."""
    assert config_hash({"enabled": True}) != config_hash({"enabled": "true"})
    assert config_hash({"enabled": True}) != config_hash({"enabled": 1})


@pytest.mark.trace("REQ-REPRO-001")
def test_a_number_written_as_a_string_is_not_the_same_config() -> None:
    assert config_hash({"lookback": 60}) != config_hash({"lookback": "60"})
    assert config_hash({"lookback": 60}) != config_hash({"lookback": 60.0})


@pytest.mark.trace("REQ-REPRO-001")
def test_a_list_keeps_its_order() -> None:
    """A list of lookbacks is not a set: `[60, 100]` and `[100, 60]` are the same
    grid searched in different orders, and a walk-forward run that stops early
    does not visit the same ones."""
    assert config_hash({"lookbacks": [60, 100]}) != config_hash({"lookbacks": [100, 60]})


@pytest.mark.trace("REQ-REPRO-001")
def test_nesting_cannot_be_flattened_away() -> None:
    """Length-prefixed, so a nested structure cannot encode identically to a
    differently-nested one carrying the same leaves."""
    assert config_hash({"a": {"b": 1}}) != config_hash({"a": [1]})
    assert config_hash({"a": {"b": {"c": 1}}}) != config_hash({"a": {"b": 1}})


@pytest.mark.trace("REQ-REPRO-001")
def test_a_null_is_a_value_and_not_an_absence() -> None:
    """`{"stop": None}` says the stop is explicitly nothing; `{}` says nobody
    mentioned a stop. Two different configs."""
    assert config_hash({"stop": None}) != config_hash({})


@pytest.mark.trace("REQ-REPRO-001")
def test_a_config_holding_something_unencodable_is_refused() -> None:
    """Falling back to `repr()` puts a memory address in the hash on some types,
    and the config then looks different on every run for a reason nobody would
    find."""

    class Opaque:
        pass

    with pytest.raises(UnhashableConfig, match="channel.model"):
        config_hash({"channel": {"model": Opaque()}})


@pytest.mark.trace("REQ-REPRO-001")
def test_a_non_string_key_is_refused() -> None:
    with pytest.raises(UnhashableConfig, match="non-string key"):
        config_hash({1: "a"})  # type: ignore[dict-item]


@pytest.mark.trace("REQ-REPRO-001")
def test_a_dataset_reference_does_not_depend_on_the_order_of_its_tables() -> None:
    """A run that listed its tables differently read the same data."""
    forward = dataset_reference({"bars": (1, "aa"), "cex_trades": (2, "bb")})
    backward = dataset_reference({"cex_trades": (2, "bb"), "bars": (1, "aa")})

    assert forward == backward


@pytest.mark.trace("REQ-REPRO-001")
def test_a_dataset_reference_changes_with_the_snapshot_and_with_the_content() -> None:
    """Both are recorded because they answer different questions: the id is how
    a reader finds the data again, the hash is what says it is the same data."""
    base = dataset_reference({"bars": (1, "aa")})

    assert dataset_reference({"bars": (2, "aa")}) != base
    assert dataset_reference({"bars": (1, "bb")}) != base
    assert dataset_reference({"trades": (1, "aa")}) != base


@pytest.mark.trace("REQ-REPRO-001")
def test_a_dataset_reference_over_no_tables_is_refused() -> None:
    """A run over nothing has no dataset to be reproducible from, and an empty
    reference would record that it does."""
    with pytest.raises(ValueError, match="no tables"):
        dataset_reference({})


@pytest.mark.trace("REQ-REPRO-001")
def test_a_table_referenced_without_a_content_hash_is_refused() -> None:
    """The id alone is a pointer, and a pointer to a table someone rebuilt is not
    a dataset."""
    with pytest.raises(ValueError, match="content hash"):
        dataset_reference({"bars": (1, "")})


@pytest.mark.trace("REQ-REPRO-001")
def test_a_table_referenced_at_snapshot_zero_is_refused() -> None:
    """Snapshots are numbered from one, so a zero here means nobody looked."""
    with pytest.raises(ValueError, match="numbered from one"):
        dataset_reference({"bars": (0, "aa")})
