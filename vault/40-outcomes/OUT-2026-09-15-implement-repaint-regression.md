---
id: OUT-2026-09-15-implement-repaint-regression
step: implement
records: [REQ-NRT-REPAINT]
commit: null
---

## What was done

Implemented [[REQ-NRT-REPAINT]] — PRD §35.3, run as its own procedure over every
channel model and every moment in a stream.

- `src/channelflow/channels/repaint.py` — `Retained`, `Divergence`, `replay`,
  `mutations`, `recomputations`.
- `tests/unit/channels/test_repaint_regression.py` — 20 tests, including three
  deliberately faulty models.
- `tests/mutations/repaint.toml`.

[[REQ-NRT-LEAK]] stays at `specified`. See "What is still open".

### A process lapse, stated plainly

**I wrote the harness before the tests.** `/sdd-implement` step 2 requires the
failing tests first, and there is therefore no RED output for this work — not
because the behaviour pre-existed, but because I took them out of order. I am
recording that rather than producing a failure that did not happen.

What stands in for it is stronger than a red run would have been: three fault
models that make the suite fail on purpose, and a mutation sweep of twelve
mutations against the harness itself.

## What was decided

**§35.3's step 4 has two readings, and both are implemented under separate
names.** Read literally, "assert all previous snapshots unchanged" tests
*mutation* — `mutations()`. Read as what the section is for, it tests
*repainting*: refit each moment once the future exists and demand the same
answer — `recomputations()`. Keeping them apart means a failure says which
happened.

**`recomputations` takes a factory, not a model.** A reused model would make the
check a measurement of the harness the day a model carries state.

**Comparison walks `model_fields` rather than a list written in the harness**, so
a field added to `ChannelSnapshot` later is compared without anyone remembering.

### The mutation sweep found two weak assertions

12 mutations. First run **10 caught, 2 survived**; both were weak tests, and both
are now killed by a new fault model rather than by an excuse.

- *`mutations` only checks the first snapshot.* `_MutatingChannel` edits **every**
  earlier snapshot on every fit, so a first-only check still saw it.
  `_LateMutatingChannel` now leaves snapshot zero alone and edits the rest, so the
  fault is visible only to a check that walks the whole stream.
- *`recomputations` reuses one model instead of building a fresh one.* All four
  shipped models are stateless — measured — so no real model can tell the two
  apart. `_StatefulChannel` answers differently depending on how many times it
  has been asked, which distinguishes them.

Second run: **12 caught, 0 survived.**

### A correction made during implementation

`_LateMutatingChannel` was first written to edit the previous snapshot on every
fit, and the test asserted the first snapshot was untouched. It was not — the
second fit edits it. The fault model now skips its first two calls, and the
expected count is `len(retained) - 2`. I had asserted the property before
checking it.

## What is still open

**[[REQ-NRT-LEAK]] is a much larger job than this note's sibling, and the number
was wrong.** The requirement first said 27 feature specifications. That was the
registry after importing only `channelflow.features.*`; three further packages
register features, and `exposed_feature_names()` — which imports all eight — is
the canonical enumeration. The real figure is **55**, one specification per
exposed name, across seven families: `derivatives` 19, `order_book` 15,
`trade_flow` 5, `order_flow` 5, `volume_structure` 5, `channel` 4, `defi` 2.

And they share no interface. Some take events with a window, some a
`BookService`, some scalars, some a stateful tracker. There is no generic
harness: 55 truncation cases have to be written by hand against 55 signatures.

That cannot be staged behind a partial gate either. A suite that passed while
most features were unchecked is the "skip that reports green" the requirement
exists to forbid, and this repository cannot commit a red suite. So
[[REQ-NRT-LEAK]] reaches `implemented` when all 55 have cases, and not before.

**§35.5 (live/replay parity)** is the third section in this family with no
requirement note. [[REQ-NRT-E]] covers replay parity for extrema only.
