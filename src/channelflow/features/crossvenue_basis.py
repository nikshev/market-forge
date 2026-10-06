"""PRD §17.3's cross-venue basis: one venue against its own consensus.

# @trace: REQ-WP-091

    venue_basis_bps = 10000 * (mid_i / consensus_mid - 1)

**The name is half the deliverable.** `basis_bps` is already registered by the
derivatives package ([[REQ-WP-030]]) for a perpetual's price against spot, and
that is a different quantity: one measures a venue against its peers, the other
a contract against the spot it tracks. A registry in which two entries answer
to one name would make the answer depend on which caller imported first, which
is why the PRD's own formula gets this name and the derivatives one keeps
theirs.

**Consensus is per market type, never blended** (spec FR-006). Spot venues are
compared with the spot consensus, perpetuals with the perpetual consensus. A
median over a spot mid and two perpetual mids would fold the spot-perp basis --
the very thing §17.1's "normalized mids" does not explain -- into the number
nominally measuring a venue's distance from its own peers, and the resulting
line would move when the basis moved for an unrelated reason.

**Point in time.** The value at `t` is taken at the bar's close from quotes
observed at or before that close, so only data with `event_time <= t` enters it
(Constitution Principle I). `point_in_time_safe` says so in the registration
rather than leaving it to be inferred, and the computation itself reads a
consensus another module already refused late quotes from.

**Absence, not zero.** Fewer than two venues of the market type contributed at
the bar close and there is no consensus to measure against -- so the feature is
absent there. Zero is the reading for a venue sitting exactly on the consensus,
and a pane drawing a flat zero through an hour of missing quotes would be
claiming agreement where there was nothing to agree with.
"""

from __future__ import annotations

from decimal import Decimal

from channelflow.features.registry import FeatureSpec, register

FEATURES: tuple[str, ...] = ("venue_basis_bps",)

#: One basis point, as PRD §17.3 writes it: `10000 * (mid / consensus - 1)`.
_BPS = 10000


def venue_basis_bps(mid: Decimal, consensus_mid: Decimal) -> float:
    """§17.3's formula in basis points: `10000 * (mid / consensus_mid - 1)`.

    Positive when the venue trades above its consensus, negative when below.

    A `float` because PRD §19 registers a feature's value as `float64` and the
    features table stores one -- the same reason `dex.active_liquidity_at`
    returns one. The arithmetic stays in `Decimal` until the last step so the
    result is the one a reader recomputes by hand.

    A non-positive consensus is refused rather than divided by: it is not a
    price, and a quotient of it would describe the refusal, not the venue.
    """
    if consensus_mid <= 0:
        raise ValueError(f"consensus mid must be positive, got {consensus_mid}")
    return float((mid / consensus_mid - 1) * _BPS)


def _register_all() -> None:
    register(
        FeatureSpec(
            name="venue_basis_bps",
            version=1,
            family="cross_venue",
            description=(
                "Viewed venue mid minus its market-type consensus mid, in basis "
                "points; spot venues against spot consensus, perp against perp, "
                "never blended."
            ),
            formula="10000 * (mid_i / consensus_mid - 1) at the bar close",
            unit="bps",
            source_events=("quote",),
            lookback="the bar",
            cadence="per final bar",
            availability_lag_ms=0,
            null_policy=(
                "absent when fewer than two venues of the venue's market type "
                "contributed at the bar close; never zero-filled"
            ),
            clipping="none",
            normalization="basis points",
            point_in_time_safe=True,
            test_fixture="tests/unit/features/test_crossvenue_basis.py",
        )
    )


_register_all()
