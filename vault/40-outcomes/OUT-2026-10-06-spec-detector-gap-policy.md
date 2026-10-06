---
id: OUT-2026-10-06-spec-detector-gap-policy
step: spec
records: [REQ-WP-087]
commit: null
---

## What was done

Read `vault/10-requirements/REQ-WP-087.md` (no `ACCEPTANCE-NOT-SPECIFIED`), constitution, and code facts (channel lookback=60, detector bar-counting, ETHUSDT 1h 148-bar hole measured), then wrote `specs/141-detector-gap-policy/spec.md` with `traces: [REQ-WP-087]`, checklist, and vault spec note.

## What was decided

- **Policy 2 (restart at gap) assumed** per requirement's recommendation. Owner confirmation needed — spec stays `draft` until confirmed.
- **Detector**: resets state on hole (> `gap_threshold` missing bars); no confirmation straddles hole.
- **Channel**: fits only to bars after hole; snapshot absent/short until `lookback` contiguous bars.
- **Threshold**: `gap_threshold` config (default 1); threshold=0 any gap restarts.
- **Confirmation lag**: adds `confirmation_lag_ns` (time) to extremum; no straddling records.
- **Built on**: REQ-WP-086 (gap marking), REQ-WP-006 (channel), REQ-WP-019 (detector).

## What is still open

- Owner confirmation of policy 2 (restart at gap) — requirement stays `draft` until confirmed.
- Live validation on ETHUSDT 1h (148-bar hole) — records before/after hole separate, zero straddling.