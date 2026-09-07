---
id: OUT-2026-09-07-plan-domain-model
step: plan
records: [REQ-WP-002]
commit: null
---

## What was done

Planned REQ-WP-002 and broke it into 16 tasks. Constitution Check passed.

## What was decided

- **This is the feature where the constitution becomes code.** Five principles
  bind rather than the usual two or three: II (two clocks, both required), III
  (frozen models), XI (byte-identical serialization, which is what makes a
  fixture a fixture), XII (Decimal and strings over speed), XIV (traceable).
  Principle I does not bind directly — these models compute nothing — but it is
  why `ingest_time_ns` must be present and distinct.
- **No `data-model.md`.** The models *are* the data model, they are typed, and a
  prose copy would drift from them within a week.
- **Split by subject, not by layer.** A connector working on order books imports
  one module. `serialization.py` is separate because the encoding convention is
  the thing most likely to change, and it should change in one place.

## What is still open

- Nothing from this step.
