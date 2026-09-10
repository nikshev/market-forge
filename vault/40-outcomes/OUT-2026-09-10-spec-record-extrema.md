---
id: OUT-2026-09-10-spec-record-extrema
step: spec
records: [REQ-WP-029]
commit: null
---

## What was done

`specs/067-record-extrema/spec.md`: three user stories, 9 functional
requirements, 7 success criteria. [[REQ-WP-029]] moves to `specified`.

## What was decided

- **Recording goes through subscribers, and the spec requires it.** A
  requirement that only asked for the rows to arrive would be met by the
  shortest path, and the bus would still have one consumer — which is the thing
  this work exists to test.
- **Publishing is per bar.** A batch at the end produces the same rows and a
  different event stream, and the difference stays invisible until a live
  process attaches the same subscribers and sees a burst.
- **Idempotence and extension are a pair.** Writing nothing on a re-run is easy
  if you also write nothing on an extension; stated together they pin
  idempotence rather than inertia.
- **The dataset identity of what the replay already wrote must not move.** That
  is the criterion that catches this feature damaging its neighbours.

## What is still open

- **Whether the bus survives a second producer.** Pre-committed: if it has to
  change, that is a finding about the bus and gets recorded as one.
- **The detector accumulates rather than calling back**, so per-bar publishing
  means noticing what it appended. Whether that reads honestly is a plan
  question, and the alternative — changing the detector — is out of scope.
