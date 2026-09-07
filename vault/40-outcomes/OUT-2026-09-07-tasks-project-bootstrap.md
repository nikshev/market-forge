---
id: OUT-2026-09-07-tasks-project-bootstrap
step: tasks
records: [REQ-WP-001]
commit: null
---

## What was done

Broke REQ-WP-001 into 18 tasks in `specs/002-project-bootstrap/tasks.md`,
grouped by the spec's three user stories so each can be implemented and verified
independently. Then ran the cross-artifact consistency analysis over `spec.md`,
`plan.md` and `tasks.md`.

## What was decided

**The analysis found two real gaps, and they were the useful kind.** FR-007
(dependencies declared in a single project file, pinned to 3.12) and SC-004
(running the start command twice equals running it once) had tasks doing the
work but no task naming the criterion. That is under-specification, not a
missing task: at review time nobody could have said whether either criterion was
met, because no task claimed it. Fixed by amending T002, T003 and T010 to cite
them. Re-ran the check: every one of the 12 FRs and 6 SCs is now referenced.

**Contradiction check came back clean.** Three terms appear across the artifacts
that would be contradictions if used positively — ClickHouse, Lightweight
Charts, and `latest` as an image tag. All three appear only as exclusions, in
every document that mentions them. Verified by reading the surrounding line, not
by counting occurrences.

**Every file the plan's structure tree names has a task.** Checked
mechanically: thirteen files, thirteen covered.

**Manual verification steps are listed as tasks (T010, T011, T013, T016, T017)
rather than left as prose.** They are checks a person runs, not automated tests,
but the spec states them as success criteria and an unlisted check is an unrun
one. Their results go in the implement-step outcome note.

**Tests are included, not optional.** The tasks template says tests are optional
unless the spec asks for them. This spec's SC-002 requires the stack be verified
by connecting to each service and performing a real operation, so T006 and T007
are written first and must fail before the compose file exists.

## What is still open

- **The `IMPLEMENTS` edge for this requirement will be a single thin link.** The
  feature's output is a compose file, a Makefile, an env example and a frontend
  scaffold — none of which the code collector scans. Only
  `src/channelflow/__init__.py` can carry a `# @trace:` comment. Recorded in
  `tasks.md` under Notes rather than papered over: manufacturing a Python file
  to carry a marker would be exactly the token gesture this repository's review
  history has spent its time removing. The `VERIFIES` edges from T006 and T007
  are the real evidence.
- **`speckit-tasks` and `speckit-analyze` were not invoked as skills.** Spec Kit
  was installed mid-session, so its skills are not in this session's registry. I
  read the tasks template through `setup-tasks.sh` and performed the consistency
  analysis directly. A fresh session will have the skills available; this is a
  session artifact, not a repository defect.
- **The MinIO image tag is still unfixed.** T008 says "pinned to explicit tags";
  which tag is chosen at implementation time against what is current and stable.
