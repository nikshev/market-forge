"""PRD section 13A.28's mandatory non-repainting tests (REQ-NRT-A..E).

Five tests in one file because the PRD states them as one mandated suite and
they are read together. Split across five files, one could quietly disappear
without the absence being obvious.

These are the deliverable, not a checking step. PRD section 2.1 names
repainting as the risk the product exists to avoid; validator rule R5 never
waives the requirements they satisfy.

Test F is absent and stays absent: it tests GMDH derivative root stability, and
there is no GMDH (ADR-023).
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from channelflow.bars import Bar
from channelflow.extrema import (
    CandidateInvalidation,
    CausalTransform,
    CenteredTransformRejected,
    DirectionalChangeDetector,
    ProminenceRule,
    ThresholdMode,
    ThresholdPolicy,
    require_causal,
)
from channelflow.extrema.causality import FORBIDDEN_IMPORTS

from .conftest import random_tail, series


def detector() -> DirectionalChangeDetector:
    return DirectionalChangeDetector(
        thresholds=ThresholdPolicy(mode=ThresholdMode.FIXED_BPS, min_bps=200.0),
        prominence=ProminenceRule(
            min_prominence_bps=0.0, min_prominence_atr=None, min_bars_between=0
        ),
    )


def swinging(count: int = 60, *, seed: int = 7) -> list[Bar]:
    """A series that actually turns, several times.

    Deterministic: a non-repainting test over a random series could not
    distinguish a regression from a different draw.
    """
    rng = random.Random(seed)
    closes: list[float] = []
    price = 100.0
    for i in range(count):
        drift = 0.012 if (i // 7) % 2 == 0 else -0.012
        price *= 1.0 + drift + rng.uniform(-0.002, 0.002)
        closes.append(price)
    return series(closes)


# --- Test A: future-bar invariance ---


@pytest.mark.trace("REQ-NRT-A")
@pytest.mark.trace("REQ-WP-019")
def test_a_appending_future_bars_changes_no_finalized_output() -> None:
    """Test A. "Compute live outputs up to `t`. Append arbitrary bars after
    `t`. Assert all finalized outputs with `available_at <= t` remain
    byte-equivalent."

    The bars appended are random, not fixed: one fixed continuation could be
    the single series a broken detector happens to survive. Three different
    seeds are tried.

    The first assertion is the one that keeps the rest honest -- comparing two
    empty lists passes, and a version of this test that only checked the count
    would pass a detector that rewrote every field.
    """
    history = swinging()
    before = detector().run(history)

    assert before, "the fixture must produce confirmations, or this proves nothing"

    for seed in (1, 2, 3):
        extended = [*history, *random_tail(len(history), 25, seed=seed)]
        after = detector().run(extended)

        # Every output that existed at `t` must still be there, unchanged.
        assert after[: len(before)] == before, (
            f"appending bars with seed {seed} changed an already-finalized output"
        )
        for original, replayed in zip(before, after, strict=False):
            assert original.model_dump() == replayed.model_dump()


@pytest.mark.trace("REQ-NRT-A")
def test_a_holds_field_by_field_not_merely_in_count() -> None:
    """The stronger reading of Test A: "byte-equivalent", not "the same number
    of them"."""
    history = swinging()
    before = detector().run(history)
    after = detector().run([*history, *random_tail(len(history), 40, seed=11)])

    for original, replayed in zip(before, after, strict=False):
        for field in type(original).model_fields:
            assert getattr(original, field) == getattr(replayed, field), field


@pytest.mark.trace("REQ-NRT-A")
def test_a_prefix_of_the_stream_gives_a_prefix_of_the_outputs() -> None:
    """Test A from the other side: truncating the future must not add outputs.

    Run over every prefix length and assert the confirmations grow only by
    appending. A detector that revised a decision would show up as a prefix
    that stops matching.
    """
    history = swinging()
    previous: list = []
    for length in range(10, len(history) + 1, 5):
        current = detector().run(history[:length])
        assert current[: len(previous)] == previous
        previous = current


# --- Test B: candidate chronology ---


@pytest.mark.trace("REQ-NRT-B")
@pytest.mark.trace("REQ-WP-019")
def test_b_an_invalidated_candidate_keeps_its_original_record() -> None:
    """Test B. "A candidate may be invalidated later, but its original snapshot
    cannot change."

    The invalidation carries the candidate's id, not the candidate, so there is
    no path from it that could modify the original even deliberately.
    """
    engine = detector()
    engine.run(swinging())
    assert engine.candidates, "the fixture must produce candidates"

    original = engine.candidates[0]
    snapshot = original.model_dump()

    engine.invalidations.append(
        CandidateInvalidation(
            candidate_id=original.candidate_id,
            invalidated_at_ns=original.observed_at_ns + 10,
            reason="superseded by a later extreme",
        )
    )

    assert engine.candidates[0].model_dump() == snapshot


@pytest.mark.trace("REQ-NRT-B")
def test_b_a_candidate_record_is_frozen() -> None:
    """The mechanism behind Test B: a value that cannot be mutated cannot be
    rewritten."""
    from pydantic import ValidationError

    engine = detector()
    engine.run(swinging())

    with pytest.raises(ValidationError):
        engine.candidates[0].price = 1  # type: ignore[misc]


# --- Test C: confirmation legality ---


@pytest.mark.trace("REQ-NRT-C")
@pytest.mark.trace("REQ-WP-019")
def test_c_known_at_is_never_before_the_extremum() -> None:
    """Test C, first half: `known_at >= extremum_time`."""
    confirmed = detector().run(swinging())

    assert confirmed
    for extremum in confirmed:
        assert extremum.known_at_ns >= extremum.extremum_time_ns
        assert extremum.confirmation_lag_bars >= 0


@pytest.mark.trace("REQ-NRT-C")
def test_c_no_confirmation_reads_a_bar_later_than_its_known_at() -> None:
    """Test C, second half: "the confirmation logic must not read events with
    `available_at > known_at`".

    Checked by running the detector over history truncated at each
    confirmation's own `known_at`. If the confirmation depended on anything
    later, it would not appear -- or would appear differently.
    """
    history = swinging()
    confirmed = detector().run(history)
    assert confirmed

    for extremum in confirmed:
        visible = [b for b in history if b.close_time_ns <= extremum.known_at_ns]
        replayed = detector().run(visible)

        assert replayed, f"nothing confirmed by {extremum.known_at_ns}"
        assert replayed[-1].model_dump() == extremum.model_dump(), (
            "this confirmation needed a bar from after its own known_at"
        )


# --- Test D: centered filter prohibition ---


@pytest.mark.trace("REQ-NRT-D")
@pytest.mark.trace("REQ-WP-019")
def test_d_a_centered_transform_is_refused_by_the_production_path() -> None:
    """Test D. "Production feature path fails validation if a transform
    declares symmetric/centered future dependence." """
    centered = CausalTransform(name="centered_ma_21", centered=True)

    with pytest.raises(CenteredTransformRejected, match="centered"):
        require_causal(centered)


@pytest.mark.trace("REQ-NRT-D")
def test_d_a_causal_transform_is_allowed() -> None:
    """The guard must not refuse everything: a rule that rejects all transforms
    would pass the test above and make the engine unusable."""
    causal = CausalTransform(name="ema_21", centered=False)

    assert require_causal(causal) is causal


@pytest.mark.trace("REQ-NRT-D")
def test_d_research_paths_are_not_guarded() -> None:
    """PRD section 13A.6: "Centered/offline peak-finding may only create labels
    and diagnostics, never live signals."

    Section 13A.4's symmetric k-neighbourhood labels are centered by
    definition. A guard applied everywhere would make the PRD's own research
    labels illegal.
    """
    centered = CausalTransform(name="symmetric_k_labels", centered=True)

    assert centered.apply([1.0, 2.0]) == [1.0, 2.0]


@pytest.mark.trace("REQ-NRT-D")
def test_d_the_engine_imports_no_centered_helper() -> None:
    """The second guard, beside the declaration (ADR-022).

    The declaration catches the honest case at the call site. This catches the
    import -- someone reaching for `savgol_filter` because it smooths better.
    Neither alone would cover the realistic mistakes.
    """
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "extrema"
    modules = [m for m in package.glob("*.py")]
    assert modules, "the package has no modules; this would pass vacuously"

    for module in modules:
        source = module.read_text()
        for forbidden in FORBIDDEN_IMPORTS:
            # `causality.py` names them in order to forbid them.
            if module.name == "causality.py":
                continue
            assert forbidden not in source, f"{module.name} uses {forbidden!r}"


# --- Test E: replay parity ---


@pytest.mark.trace("REQ-NRT-E")
@pytest.mark.trace("REQ-WP-019")
def test_e_a_replayed_stream_matches_the_live_run_exactly() -> None:
    """Test E. "Live recorded outputs and deterministic replay outputs must
    match for the same event stream/config/model artifact." """
    history = swinging()

    live = detector().run(history)
    replay = detector().run(history)

    assert live
    assert [e.model_dump() for e in live] == [e.model_dump() for e in replay]


@pytest.mark.trace("REQ-NRT-E")
def test_e_feeding_one_bar_at_a_time_matches_feeding_the_whole_series() -> None:
    """Test E's real content: the *same code* live and in replay (Principle
    VII). A detector behaving differently when fed incrementally would have two
    implementations, and only one of them would be the one in production.
    """
    history = swinging()

    batch = detector().run(history)

    incremental = detector()
    for one in history:
        incremental.on_bar(one)

    assert [e.model_dump() for e in incremental.confirmed] == [e.model_dump() for e in batch]


@pytest.mark.trace("REQ-NRT-E")
def test_e_a_different_configuration_gives_a_different_answer() -> None:
    """Guard on Test E: parity means same stream *and* same config. A detector
    ignoring its configuration would pass every parity test ever written."""
    history = swinging()

    loose = DirectionalChangeDetector(
        thresholds=ThresholdPolicy(mode=ThresholdMode.FIXED_BPS, min_bps=100.0),
        prominence=ProminenceRule(
            min_prominence_bps=0.0, min_prominence_atr=None, min_bars_between=0
        ),
    ).run(history)
    strict = DirectionalChangeDetector(
        thresholds=ThresholdPolicy(mode=ThresholdMode.FIXED_BPS, min_bps=900.0),
        prominence=ProminenceRule(
            min_prominence_bps=0.0, min_prominence_atr=None, min_bars_between=0
        ),
    ).run(history)

    assert len(loose) > len(strict)


# --- the cross-cutting rule ---


@pytest.mark.trace("REQ-WP-019")
def test_the_extrema_package_cannot_consult_a_clock() -> None:
    """SC-010, FR-012.

    Every timestamp in this engine is a bar's own event time. A clock would
    make a replayed stream produce different records, and Test E would be
    testing the clock rather than the engine.
    """
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "extrema"
    modules = list(package.glob("*.py"))
    assert modules

    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"
