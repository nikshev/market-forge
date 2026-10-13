---
id: OUT-2026-10-13-implement-venue-basis-cost
step: implement
records: [REQ-WP-107]
commit: null
---

## What was done

Specified, planned and implemented [[REQ-WP-107]] (spec 159) in one step.

## Evidence

**Found by profiling, not by guessing**: inside the API container `feature_points` took 0.75 s and the table read 0.9 s while the HTTP
request took 3.8 s -- so it was not the read. The route's venue-basis merge scanned every quote for every bar. **RED first**: the speed test
failed (a second of work was exceeded). **GREEN**: the api and crossvenue suites; mutation sweep `venue_basis_quotes` 6 caught, 0 survived
(one survivor, the ordering mutation, exposed a test that passed by luck and was strengthened).

**Deployed**: the features series answers in **1.1 s** (3.8 s before).

## What is still open

- The rest of the 1.1 s is the table read and the consensus merge; nothing further planned.
