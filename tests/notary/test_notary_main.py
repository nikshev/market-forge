# @trace: REQ-INFRA-007
"""The service: configuration, the visible outbox, the metrics, a loop that survives (FR-008)."""

from __future__ import annotations

import pytest

from channelflow.lakehouse import Catalog
from channelflow.notary import main as service
from channelflow.notary.config import ConfigError
from channelflow.notary.submitter import Submitter, SubmitterConfig
from tests.notary.conftest import SECOND, FakeNotaryChain, record_row, register

BASE_ENV = {
    "CHANNELFLOW_CATALOG_URI": "sqlite:///x.db",
    "CHANNELFLOW_WAREHOUSE": "/tmp/warehouse",
    "MONAD_NOTARY_ADDRESS": "0x4a0963b8B35311411Bf17497F0CAeD20d5596682",
    "MONAD_NOTARY_DEPLOY_BLOCK": "69218030",
    "CHANNELFLOW_NOTARY_KEYSTORE": "/run/secrets/notary_keystore",
    "CHANNELFLOW_NOTARY_PASSWORD_FILE": "/run/secrets/notary_password",
}
T = 1_791_450_000


@pytest.mark.trace("REQ-INFRA-007")
@pytest.mark.parametrize(
    "missing",
    [
        "MONAD_NOTARY_ADDRESS",
        "MONAD_NOTARY_DEPLOY_BLOCK",
        "CHANNELFLOW_NOTARY_KEYSTORE",
        "CHANNELFLOW_NOTARY_PASSWORD_FILE",
    ],
)
def test_every_missing_required_variable_is_named(missing: str) -> None:
    env = {k: v for k, v in BASE_ENV.items() if k != missing}
    with pytest.raises(ConfigError, match=missing):
        service.ServiceConfig.from_env(env)


@pytest.mark.trace("REQ-INFRA-007")
def test_the_defaults_are_the_planned_ones_and_units_are_converted() -> None:
    config = service.ServiceConfig.from_env(BASE_ENV)

    assert config.rpc_url == "https://testnet-rpc.monad.xyz" and config.chain_id == 10143
    assert config.interval_s == 60.0
    assert (
        config.submitter.window_ns == 30 * 60 * SECOND
    )  # the plan's default: a root per 30 minutes
    assert config.submitter.max_batch == 5000
    assert config.submitter.min_balance_wei == 10**17  # 0.1 MON
    assert config.submitter.max_gas_price_wei == 500 * 10**9
    assert config.submitter.submit_timeout_ns == 120 * SECOND
    assert config.gas_margin == 1.05 and config.deploy_block == 69_218_030


@pytest.mark.trace("REQ-INFRA-007")
def test_overrides_use_the_same_duration_grammar_as_the_other_loops() -> None:
    config = service.ServiceConfig.from_env(
        BASE_ENV
        | {
            "CHANNELFLOW_NOTARY_BATCH_WINDOW": "1h",
            "CHANNELFLOW_NOTARY_INTERVAL": "30",
            "CHANNELFLOW_NOTARY_GAS_MARGIN": "1.1",
            "CHANNELFLOW_NOTARY_MIN_BALANCE": "250000000000000000",
        }
    )
    assert config.submitter.window_ns == 3600 * SECOND and config.interval_s == 30.0
    assert config.gas_margin == 1.1 and config.submitter.min_balance_wei == 25 * 10**16


@pytest.mark.trace("REQ-INFRA-007")
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("CHANNELFLOW_NOTARY_BATCH_WINDOW", "soon"),
        (
            "CHANNELFLOW_NOTARY_GAS_MARGIN",
            "0.9",
        ),  # under 1 would send transactions that run out of gas
        ("CHANNELFLOW_NOTARY_MAX_BATCH", "0"),
        ("MONAD_NOTARY_ADDRESS", "not-an-address"),
        ("MONAD_NOTARY_DEPLOY_BLOCK", "yesterday"),
    ],
)
def test_a_malformed_value_names_its_variable(name: str, value: str) -> None:
    with pytest.raises(ConfigError, match=name):
        service.ServiceConfig.from_env(BASE_ENV | {name: value})


@pytest.mark.trace("REQ-INFRA-007")
def test_the_outbox_listing_says_what_waits_and_why(catalog: Catalog) -> None:
    register(
        catalog,
        record_row("waiting", T, registered_at_ns=T * SECOND),
        record_row("broken", T, notarizable="no"),
    )
    chain = FakeNotaryChain(down=True)
    submitter = Submitter(
        catalog=catalog,
        chain=chain,
        config=SubmitterConfig(
            window_ns=0,
            max_batch=10,
            min_balance_wei=0,
            max_gas_price_wei=10**12,
            submit_timeout_ns=1,
        ),
        now_ns=lambda: T * SECOND + 600 * SECOND,
    )
    submitter.tick()

    text = service.render_outbox(catalog, now_ns=T * SECOND + 600 * SECOND)

    assert "unconfirmed batches: 1" in text and "unnotarizable records: 1" in text
    assert "connection refused" in text  # the last error is shown, not hidden
    assert "broken" in text and "commit absent" in text  # an unnotarizable record, with its reason
    assert "oldest pending: 600" in text


@pytest.mark.trace("REQ-INFRA-007")
def test_the_gauges_are_exposed_with_the_outbox_numbers(catalog: Catalog) -> None:
    register(catalog, record_row("a", T, registered_at_ns=T * SECOND))
    chain = FakeNotaryChain()
    registry = service.new_registry()
    service.update_metrics(registry, catalog, chain, now_ns=T * SECOND + 100 * SECOND)

    text = registry.render()
    for name in (
        "channelflow_notary_unbatched_records",
        "channelflow_notary_unconfirmed_batches",
        "channelflow_notary_oldest_pending_age_seconds",
        "channelflow_notary_unnotarizable_records",
        "channelflow_notary_balance_wei",
    ):
        assert f"# TYPE {name} gauge" in text, name
    assert "channelflow_notary_unbatched_records 1" in text
    assert f"channelflow_notary_balance_wei {chain.balance}" in text
    assert "channelflow_notary_oldest_pending_age_seconds 100" in text
    # Nothing has been committed, so there is no 'last commit' to report: absent, not zero.
    assert "last_confirmed_block_time" not in text

    submitter = Submitter(
        catalog=catalog,
        chain=chain,
        config=SubmitterConfig(
            window_ns=0,
            max_batch=10,
            min_balance_wei=0,
            max_gas_price_wei=10**12,
            submit_timeout_ns=1,
        ),
        now_ns=lambda: T * SECOND + 100 * SECOND,
    )
    submitter.tick()
    service.update_metrics(registry, catalog, chain, now_ns=T * SECOND + 100 * SECOND)
    rendered = registry.render()
    assert f"channelflow_notary_last_confirmed_block_time_seconds {chain.block_ts}" in rendered
    assert "channelflow_notary_unconfirmed_batches 0" in rendered


@pytest.mark.trace("REQ-INFRA-007")
def test_the_metrics_survive_an_unreachable_chain(catalog: Catalog) -> None:
    registry = service.new_registry()
    chain = FakeNotaryChain(down=True)
    service.update_metrics(registry, catalog, chain, now_ns=T * SECOND)  # must not raise

    assert "channelflow_notary_unbatched_records 0" in registry.render()
    assert "channelflow_notary_balance_wei" not in registry.render()  # unknown, not zero


@pytest.mark.trace("REQ-INFRA-007")
def test_the_loop_continues_after_a_tick_that_raises(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = {"n": 0}

    def tick(self: Submitter) -> object:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("a bug in the first tick")
        raise KeyboardInterrupt  # stop the test after the second

    monkeypatch.setattr(Submitter, "tick", tick)
    submitter = Submitter(
        catalog=catalog,
        chain=FakeNotaryChain(),
        config=SubmitterConfig(
            window_ns=0,
            max_batch=10,
            min_balance_wei=0,
            max_gas_price_wei=10**12,
            submit_timeout_ns=1,
        ),
        now_ns=lambda: T * SECOND,
    )

    with pytest.raises(KeyboardInterrupt):
        service.serve(submitter, catalog, FakeNotaryChain(), service.new_registry(), interval_s=0.0)

    assert calls["n"] == 2  # the first tick's failure did not end the loop
    assert "a bug in the first tick" in capsys.readouterr().out
