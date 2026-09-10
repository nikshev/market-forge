---
id: OUT-2026-09-10-plan-stop-latency
step: plan
records: [REQ-WP-033]
commit: null
---

## What was done

`specs/071-stop-latency/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/latency.md`, `quickstart.md`. [[REQ-WP-033]] moves to `planned`.

## What was decided

- **One variable becomes two, and that is the whole change.** The stop the
  policy has *decided* and the stop the exchange is *obeying* are one variable
  today. Triggers go against the active one; the policy is shown the decided
  one, because a live engine knows what it asked for. Shown the active stop, a
  policy re-proposes the same movement at every point until the acknowledgement
  lands — inflating the update count, burning the cooldown, and producing a
  reason histogram describing an engine with amnesia rather than a market with
  latency.
- **`stop_updates` keeps its meaning and gains a companion.** Decisions made,
  and decisions obeyed inside the path. Collapsing them makes the spec's own
  edge case unobservable: a latency longer than the path leaves a position on
  its initial stop while the report says the stop moved four times.
- **The default's total is a floor and says so.** 160 ms on the network leg,
  which is what §44A.27's example measures; zero on the decision and computation
  legs, which the PRD never quantifies. Inventing plausible values for those two
  would put a number that looks measured where a floor belongs.
- **Negative legs are refused.** A stop obeyed before it was decided is not a
  slow exchange; it is a broken model.

## The claim this plan has to verify rather than assume

Existing paths step a minute at a time and the default latency is 160 ms, so
every decision should be active by the next observation and **no existing
outcome should move**. That is the safety argument for landing a behaviour
change under a non-zero default, and it is only worth anything if it is checked:
the 20 existing replay tests must pass untouched. If one moves, the default is
reaching past the example it came from, and the default is wrong.

## What is still open

- Nothing new. The three from [[OUT-2026-09-10-spec-stop-latency]] stand:
  the two unmeasured legs, what an ambiguous outcome should do to a comparison,
  and intra-bar ordering, which needs an OHLC path model.
