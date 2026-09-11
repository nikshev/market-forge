---
id: OUT-2026-09-11-implement-backup-restore
step: implement
records: [REQ-WP-037]
commit: null
---

## What was done

`lakehouse/backup.py`: `back_up`, `restore`, `verify`, all store-to-store over
the existing port. 23 unit tests and 4 integration tests against MinIO. 18 of 19
mutants caught; the nineteenth is recorded below as equivalent, and finding it
corrected an error in this requirement's own reasoning.

RED first: the test module failed to import `TargetNotEmpty`.

## The claim that was wrong

The spec, plan, research and module docstring all said the obvious
implementation — list every key under the table prefix and copy it — was
**wrong**, because a sorted listing returns `<table>/metadata/...` before
`<table>/data/...` and therefore copies manifests first.

**It does not.** `data` sorts before `metadata`. The listing implementation
copies data first and is safe for this key layout.

The mutation sweep found it the only way this could have been found: the mutant
that replaced the snapshot walk with a key listing **survived every test**. A
survivor usually means a missing assertion; this one meant the thing I had
called a bug was not one.

The design did not change, and the reason for it did. The walk satisfies
`table.py`'s ordering **by construction** — it reads each manifest and copies
what that manifest names before the manifest itself. The listing satisfies it
**by coincidence of two directory names**, and nothing would notice the day that
stopped holding. That is a weaker argument than the one first written, and it is
the true one. All five documents and both docstrings now say so, and the mutant
is recorded as equivalent rather than chased.

Worth keeping: the failure mode here was a confident causal story that no test
could contradict, written into four artifacts before a line of code existed.

## What else the sweep found

- **Only the newest snapshot verified.** Manifests are cumulative, so the newest
  one names every data file and checking it alone looks complete. What it misses
  is the history *behind* it: a missing intermediate manifest leaves the latest
  read working and every point-in-time read before it broken. The parent chain
  is now followed, and the first test for it only reached one link back — a hole
  next to the newest commit — so a second test puts the hole three links down.
- **Overwriting a differing object**, and **`put` instead of `put_if_absent`**.
  Both were covered only by the integration test, which the sweep does not run.
  Two unit tests now pin them: a re-run copies zero objects, and a key already
  holding something else is refused.

## What was decided while building

- **Manifests turned out to be cumulative**, which two of my tests assumed
  otherwise. A file from the first commit is named by every later manifest, so
  `verify` reports each finding once — four lines for one problem buries the
  other three.
- **`without()` builds a damaged store by copying, not deleting.** The port has
  no `delete` and should not grow one for a test, and "a copy that lost a file"
  is the honest shape of the scenario anyway.
- **`WouldLandShort` fires on a detectable condition.** A backup missing its
  newest *manifest* is indistinguishable from one that never had it; a backup
  whose newest manifest names an absent file is not. The second is the shape a
  damaged copy actually has, and the test was rewritten to it.

## What is still open

- **Incremental backup**, and **where a backup lives** — both from the spec.
- **Nothing schedules a backup.** This is the mechanism; running it belongs with
  deployment, which is Phase 8's own separate deliverable.
