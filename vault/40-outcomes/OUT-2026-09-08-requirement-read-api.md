---
id: OUT-2026-09-08-requirement-read-api
step: spec
records: [REQ-API-001]
commit: null
---

## What was done

`REQ-API-001` extracted from PRD §28, hand-written rather than produced by
`tools/extract_prd.py`.

## What was decided

- **The extractor missed it because it walks the work-package and phase lists,
  and §28 is a specification section no work package names.** REQ-WP-009's
  chart cannot exist without an API, which is what surfaced the omission —
  four requirements into the dependency chain, not at extraction time.
- **`as_seen_then=true` is written into the requirement body, not left to the
  spec.** PRD §27.5 calls the historical-versus-current distinction a critical
  UI feature that "directly exposes repaint-like differences and protects
  research integrity". A default that drifted to `false` would silently turn
  every deep link into a refit — the exact repainting this product exists to
  make visible.
- **`min_score`, `setup_type`, score breakdown and model probabilities stay in
  the requirement text and out of the first implementation.** The ranker is
  PRD §43 and a model is forbidden by Principle IV until baselines pass
  leakage tests. Quoting the PRD faithfully and scoping the spec is the honest
  split; paraphrasing the PRD to match what is buildable would lose the
  record of what is owed.

## What is still open

- **Other specification sections may be similarly unextracted.** §29's storage
  model and §35's test requirements are candidates. This is deferred
  extraction work, the same class as §35.3/§35.4 for validator rule R5.
