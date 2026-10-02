---
id: OUT-2026-10-02-tasks-ingest-resilience
step: tasks
records: [REQ-WP-078]
commit: null
---

## What was done

Broke [[REQ-WP-078]] into 65 tasks in `specs/123-ingest-resilience/tasks.md`, then ran the
cross-artifact analysis over spec, plan and tasks. It found seventeen things; three were
serious, and all but the cosmetic ones are fixed in the artifacts. The list is now 70 tasks,
18 functional requirements, and a coverage table the file did not have.

## What was decided

**The analysis found a contradiction in the order of work, and it was a data-safety one.**
The first draft put the live migration (T049, T050) in the archive phase, right after the
code that fixes the key, with a note that it should "follow T040 so nothing new is written to
the old keys". T040 is merged code. What stops the old keys being written is a **rebuilt
container**, T062, and the tool is in the application image only after that rebuild too. Run in
the drafted order, the migration would have raced with the old daemons still writing the
objects it was moving, and the dry-run could not even have started inside the container. T049
and T050 now follow T062, and the dependency text says why.

**A guarantee stated in two places had no test.** The spec's edge case and
`contracts/connector.md` guarantee 5 both say a reconnect loses nothing the daemon holds: the
bars builder and the archive buffer outlive the socket. Not one of the sixty-five tasks tested
it. A plausible implementation of the new reconnect — rebuilding the daemon's collaborators —
would pass every other test in the list and lose a minute of frames on every reconnect. T020a
drives it through `IngestDaemon`, with frames before and after the kill, and reads the object.

**"Configurable" held in the code and not on the host.** FR-005 and Principle X make the silence
limit configuration, and the plan names `CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS`. The tasks
added it to `.env.example` and to the settings reader — and to nothing that reaches a
container. Compose forwards only the variables a service names, so the setting would have been
unreachable in the deployment, and `CHANNELFLOW_LOG_LEVEL` with it. T053a is the test that
every ingest service names both; T056a is the wiring.

**Four smaller gaps, each closed:**

- FR-005 asks for a stated basis for each default; T005 set the number and said nothing about
  where the basis goes. It is now a comment beside each value, with the measured gaps and the
  excluded restart gap.
- FR-011 says the key test uses "the deployment's own" archive URI; T035 had a literal copied
  into the test, which lets the compose value drift away from what is tested. It now reads the
  value from the compose file.
- The plan decided Binance has no rejection frame, and the spec's FR-003 did not say so. The
  spec now states it as an assumption.
- SC-004's "under 10 MB a day" was not a pass condition anyone could check. T063 now states it
  as 6,944 bytes a minute and fails any service above it.

**Two findings that came from this session's own failures.** `ingest.toml` went red on
2026-10-02 because REQ-WP-076 rewrote the code four of its mutation patterns pointed at, and
nothing said so for a week. This change edits six mutated sources; T058 now runs
`test_mutate.py` first and after each of them. And T062 recreates **every** service, because a
logging block changes every service's configuration: the task now says what that costs
(up to fifteen buffered bars per ingest process, a short API outage) instead of leaving a
reader to discover it.

**A case the spec made and the tasks did not follow.** The archive key uses the symbol as
configured; the migration writes the upper-case spelling. A deployment configured with
`btcusdt` would split one instrument across two directories. FR-018 and T037a/T040a refuse a
lower-case Binance or Bybit symbol at start-up, so the two agree by construction.

**What the analysis got wrong, or could not see.** It flagged that `tasks.md` mentions `FR-014`
and no other requirement by identifier — true, and fixed by the coverage table — but that is a
property of the house style as much as of this file: `117`'s tasks do the same. And it cannot
see that T001's "before" is measured while the defects are still live and so moves; the task
says so, but only a reader notices.

## What is still open

- **`[US]` labels are absent from the tasks.** The phases are named for their stories, which
  carries the mapping, but the template's `[Story]` field is empty. Left, as in the other task
  lists in this repository.
- **T062's cost on a shared host.** It recreates `postgres` and `minio`. They are bind-mounted
  and addressed by name, so it is safe, and it is still the first time a recreate is planned
  rather than reached for during a repair.
- **The migration is irreversible by `git revert`** (T049, T050). Its design makes it safe;
  nothing makes it undoable. Said in the task and here.
- **Figures differ between artifacts** for the busiest log (1.1 GB a day in the spec, 830 MB in
  the plan): one is a six-day average and the other a 60-second window. The spec now says so;
  the numbers have not been reconciled because they are measurements of different things.
