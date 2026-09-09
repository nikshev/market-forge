# Deriving acceptance criteria for Phases 5, 6 and 8

**Date**: 2026-09-09
**Requirements**: `REQ-PHASE-5`, `REQ-PHASE-6`, `REQ-PHASE-8`

## Why this document exists

Eight of the PRD's eleven phase sections state their own acceptance criteria
under the deliverable list. Three do not: §45's Phase 5, Phase 6 and Phase 8 stop
after their bullets. Those three notes have carried the
`ACCEPTANCE-NOT-SPECIFIED` marker since extraction, and a requirement cannot
honestly leave `draft` while nobody can say what would satisfy it.

The criteria below are **derived**, not quoted. Each one names the PRD section it
comes from, so a reader can disagree with the derivation rather than with an
unattributed rule. The PRD itself is unchanged and unchangeable.

Same standard as the earlier derivations for `REQ-WP-016`
(`2026-09-08-cross-venue-acceptance-design.md`) and for EXP-003 through EXP-010
(`2026-09-09-experiment-acceptance-design.md`): a criterion is only written down
when some section of the PRD already implies it, and the derivation says which.

---

## Phase 5 — Cross-venue

Deliverables: Bybit; OKX; normalized symbol mapping; consensus mid; cross-venue
basis; depth comparison; funding dispersion.

Every one of those is specified somewhere else in the PRD. §17 is the Cross-Venue
Engine and §35.6 is the connector contract standard.

| Derived criterion | From |
| --- | --- |
| Each venue connector implements the shared canonical interface and passes the connector contract tests — snapshot/delta rules, reconnect, malformed events, rate limits, time parsing. | §35.6; PRD §0 item 10 (`REQ-PRIN-010`) |
| A symbol that cannot be resolved to a canonical instrument is refused rather than dropped or guessed. | §17's "same underlying" premise; [[ADR-045]]'s standing rule that a partly-readable set is discarded whole rather than silently narrowed |
| The consensus mid is the median of normalized mids across the venues that reported at the same instant; a venue that did not report is excluded rather than carried forward. | §17.1; §32's `STALE` health state |
| Cross-venue basis is exactly `10000 * (mid_i / consensus_mid - 1)`. | §17.3, verbatim |
| Depth is reported per venue at the 10/25/50 bps bands, and the best effective execution venue is named for a fixed notional. | §17.4 |
| Funding dispersion is reported across venues, and a venue whose funding is stale is excluded rather than reused. | §17's fragmentation intent; Phase 3's own criterion, "stale REST polling cannot silently reuse old value" |
| No cross-venue correlation is converted into a trading rule without out-of-sample validation. | §17.2, verbatim |

**What is deliberately not a criterion.** §17.1 offers a volume/depth-weighted
median as "experimental". An experimental alternative is not an acceptance
condition, and requiring it would make the phase unsatisfiable by the method the
PRD actually recommends.

---

## Phase 6 — Research-grade validation

Deliverables: point-in-time dataset builder; event replay; walk-forward runner;
ablation reports; experiment registry; dataset hashes; reproducible reports.

§24 specifies the dataset, §25 the replay, §35 the tests, §41 the anti-bias
rules, and PRD §0 item 13 the reproducibility contract.

| Derived criterion | From |
| --- | --- |
| Every dataset row satisfies `source_max_event_time <= as_of_time`, and a join that would violate it is refused rather than corrected. | §24.1's stated invariant |
| Labels may use future data and features may not, checked by a test rather than asserted in prose. | §24.2 |
| Primary evaluation uses chronological walk-forward splits with purge/embargo where horizons overlap; no random train/test split. | §24.3; §41 rule 1 (`REQ-BIAS-001`) |
| An ablation report names every arm that could not be run, and why, rather than omitting it. | §23.6's own practice of naming unrun baselines; [[ADR-044]] |
| An experiment is identified by the four hashes §0 item 13 names — dataset, config, code commit, model artifact — and a report that cannot name all four is refused. | PRD §0 item 13 (`REQ-PRIN-013`) |
| Re-running an experiment from the same four hashes reproduces its numbers exactly. | PRD §0 item 13; Constitution Principle XI |
| A live event segment replayed offline reproduces feature, channel and signal values. | §35.5 |

**What is deliberately not a criterion.** §24.3 says "apply purge/embargo *where*
overlapping horizon would contaminate validation". The criterion asks for purge
and embargo where horizons overlap, not unconditionally — an unconditional
embargo on non-overlapping labels discards evidence for no gain.

---

## Phase 8 — Production hardening

Deliverables: Redpanda/Kafka optional; S3 cold retention; monitoring dashboards;
alerting on data outages; backup/restore; deployment docs; load tests.

§32 defines data-quality health, §33 observability, §34 security and §36 the
performance targets.

| Derived criterion | From |
| --- | --- |
| The stream transport can be switched off and the system still runs end to end. | §45's own word, "optional" |
| Cold retention writes an object and reads it back byte-identical. | §29's canonical-persistence intent |
| Every metric §33 names is exported, and a metric with no source is absent rather than reported as zero. | §33; the "absent is not zero" rule this repository applies everywhere else |
| A data outage raises an alert naming the feed and the gap, and the affected feature family moves to `STALE` rather than continuing to serve. | §32's health states and eligibility rules; §33's "stale feed count" |
| A backup restores into an empty database and replays to the same state. | §35.5's parity standard, applied to storage rather than to a feed |
| Deployment documentation brings the stack up from a clean machine. | §45's deliverable, read against §37's repository layout |
| Load tests demonstrate §36's targets, and a target that is not met is reported rather than omitted. | §36; the same reporting rule as the ablation criterion above |
| No secret is committed, and secrets are redacted from logs. | §34 |

**What is deliberately not a criterion.** §36 ends with "do not promise
sub-millisecond HFT behavior", so no latency criterion is written tighter than
the numbers §36 states. §33 marks OpenTelemetry tracing "optional after MVP",
which is not an acceptance condition either.

---

## What this changes

The three notes lose the `ACCEPTANCE-NOT-SPECIFIED` marker and gain the criteria
above. It does **not** make any of the three phases satisfied — Phases 5, 6 and
8 each still have deliverables nothing in this repository provides, and the
phase notes say which. Writing down what would satisfy a phase is what lets a
note leave `draft`; it is not a claim that the phase is done.
