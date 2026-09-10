# Phase 0 — Research

## 1. Absent, or balanced?

**Decision**: `float | None`, with no default that fills the gap.

**Rationale**: this is the requirement. A ratio of 1.0 is a reading — longs and
shorts are even. An absent ratio is the absence of a reading. Every venue that
does not publish positioning would otherwise present as a calm, balanced book,
and the calm would be indistinguishable from the real thing at every point
downstream.

The mutation sweep confirms the cost of getting it wrong is invisible: replacing
`ratio` with `ratio or 1.0` produces a number for every instrument on every
venue, forever, and no assertion on a value would ever notice.

**Alternatives considered**: a sentinel (`-1.0`, `NaN`). Rejected — both are
floats, both survive arithmetic, and both arrive somewhere as a number.

## 2. Where does the crowding measure come from?

**Decision**: `z_score` from `derivatives/state.py` — the one funding and open
interest already use.

**Rationale**: two implementations of "too few observations to say" would drift,
and the drift would be invisible, because both would return numbers. Reuse also
inherits [[ADR-026]]: the z-score refuses rather than returning zero, and zero is
the most meaningful value a z-score can take. A crowding feature that says
"exactly average" whenever it has nothing to say reads as a calm market to
everything downstream — which is the one reading a squeeze indicator must never
give by accident.

## 3. What counts as an observation?

**Decision**: only states that actually published a ratio.

**Rationale**: a silent venue must not drag the score toward anything. A gap is
not an observation of the mean.

Asserting this needed care. The obvious test — 20 published readings, 20 silent
states, window 20 — passes whether or not silence counts, because 20 readings
fill the window either way. The test asks for window 40 instead: it can only
succeed by counting silence, and the refusal names the 20 it found.

## 4. Fresh relative to what?

**Decision**: the newest *published reading*, not the newest state.

**Rationale**: found by the mutation sweep, which is the honest way to record
it. A venue that keeps sending states and stops sending positioning is stale in
exactly the way the freshness rule exists to refuse — and measured against the
newest state it reads as current, while the connector's health looks fine. Two
mutants (checking the state, and not checking at all) both survived the first
test set, because the z-path had no freshness test of any kind.

## 5. One ratio or two?

**Decision**: two, independent.

**Rationale**: a venue's global account ratio counts accounts; its top-trader
ratio measures the positions of its largest ones. They answer different
questions and diverge exactly when the divergence matters — the crowd long while
the large accounts are short. Averaged, the number describes neither population.
A venue may also publish one and not the other, which the pair allows and a
single field would not.
