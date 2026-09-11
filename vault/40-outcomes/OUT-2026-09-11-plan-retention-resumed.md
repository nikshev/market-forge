---
id: OUT-2026-09-11-plan-retention-resumed
step: plan
records: [REQ-WP-038]
commit: null
---

## What was done

`specs/076-retention/` completed — the plan's stop section replaced, plus
`data-model.md` and `quickstart.md` — and [[ADR-062]]. [[REQ-WP-038]] moves to
`planned`.

## The stop that turned out to be half a stop

Planning stopped twice over, and the two halves had different fates.

**The mechanism was genuinely blocked.** Expiry freed nothing on the hand-rolled
plane, because nothing that plane offered could make a data file unreferenced.
[[ADR-060]] and [[REQ-WP-039]] fixed that; Iceberg has the operation.

**The second half was not a decision at all**, and I had filed it as one. I
flagged "retention makes point-in-time reads before the cutoff stop working" as
a call for whoever owns the trading system. PRD §6.4.9 asks for retention tiers
in as many words, so *that data ages out* was decided by the document this
repository implements. What §6.4.9 pointedly declines to decide is **how long**,
and that is the part the feature must not decide — every duration is an
argument, and the operator choosing one is choosing what their system forgets.

Worth recording because escalating a settled question is not a free kind of
caution: it stalls work and it teaches whoever is asked that the escalations are
noise. The useful half of that stop was the mechanism; the other half I should
have resolved by reading §6.4.9 again.

## What [[ADR-062]] gives up

[[ADR-059]] made deletion a capability the table layer could not be handed: a
narrower port with no `delete`, and a type error for anyone who tried. Iceberg's
`FileIO` carries `delete` beside the reads every table already does, so there is
no narrower port to hold and the guarantee is gone.

What replaces it is a test that reads the source and fails if any module but
`retention.py` calls `delete` on an IO — the same shape as the import checks
`test_isolation.py` runs for §29.0's layering rule. **Weaker than a signature
and stronger than a convention**, and recorded as weaker.

The general cost is worth naming past this rule: adopting a format means
adopting its capability surface, and Iceberg's is wider than the port it
replaced. The conveniences and the sharp edges arrive together, and the sharp
edges do not come with our opinions attached.

## What is still open

- **Nothing produces the pinned set.** `Registration` still does not record
  which dataset snapshot a model trained on, which is the finding this
  requirement's extraction produced and which remains its own work.
- **Nothing schedules a pass.**
