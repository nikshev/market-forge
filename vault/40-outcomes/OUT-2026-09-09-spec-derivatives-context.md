---
id: OUT-2026-09-09-spec-derivatives-context
step: spec
records: [REQ-EXP-006]
commit: null
---

## What was done

`specs/039-derivatives-context/spec.md`: three user stories, 10 functional
requirements, 10 success criteria.

## What was decided

- **Declared edges, not sample quantiles.** Two studies over different windows
  have to bucket the same reading the same way.
- **A missing variable is not a bucket.**
- **The point-in-time flag is required**, and the report's note is generated
  from it.
- **One variable at a time.** A joint conditional needs far more setups than
  these buckets will hold.

## What is still open

- **Nothing produces the observations.** Reading a funding z-score at signal
  time is pipeline work.
