---
id: OUT-2026-09-08-plan-ofi-lob-features
step: plan
records: [REQ-WP-011, REQ-PRIN-008]
commit: null
---

## What was done

Five modules under `src/channelflow/features/` — registry, instant, ofi, flow,
walls — and five test files, one per user story.

## What was decided

- **The registry is a Python module, not the YAML of PRD §19's example.** A
  registration and its implementation drift the moment they live in separate
  files, and the test that catches drift can only compare what it can import.
  The entries carry §19's sixteen fields verbatim, so nothing is lost but the
  file format.
- **The registry is built first, before any feature.** Written afterwards it
  would document whatever got built; written first it is the shape each feature
  has to fit. [[ADR-015]]'s gate depends on that order.
- **One module per feature family**, split by what each is a function *of*: a
  book state, a pair of consecutive states, a trade stream, a tracked history.
  That boundary means each test file needs one kind of fixture instead of four.
- **The wall tracker takes an interval, not a stream.** Each observation
  receives the current book and the trades since the previous one, which keeps
  [[ADR-014]]'s `min(decrease, traded)` local instead of making the tracker
  hold trade history it would then have to trim.

## What was rejected

- **Asserting features against a second implementation of their formula.**
  It passes whenever both copies are wrong the same way. Every expected value
  in these tests is hand-computed and written as a literal.
- **One `features.py`.** It would need every fixture kind in one file, and the
  families have nothing in common but the word.

## What is still open

- Nothing from this step.
