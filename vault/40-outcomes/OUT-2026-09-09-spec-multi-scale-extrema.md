---
id: OUT-2026-09-09-spec-multi-scale-extrema
step: spec
records: [REQ-EXP-016]
commit: null
---

## What was done

`specs/049-multi-scale-extrema/spec.md`: three user stories, 13 functional
requirements, 15 success criteria.

## What was decided

- **Two numbers per rule.** The change in the average trade and the change in
  the total. EXP-016's last sentence is a warning about the first being reported
  alone.
- **Only a closed higher-timeframe frame is visible**, and frames out of closing
  order are refused.
- **The rejected candidates are priced.** EXP-016 names "aligned/conflicted" as
  a pair.
- **The zone includes its own edges**, because that is where the candidates the
  rule exists to select actually are.

## What is still open

- **The candidates, their outcomes and the frames are supplied.** Detecting,
  pricing and building them belong to [[REQ-WP-019]], [[REQ-BT-001]] and the
  channel layer.
