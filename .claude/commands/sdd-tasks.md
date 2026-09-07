---
description: Break a planned requirement into tasks and check cross-artifact consistency
argument-hint: <REQ-ID>
---

Break down `$ARGUMENTS`.

1. Invoke the `speckit-tasks` skill. It reads the plan and design artifacts
   for the current feature (via `.specify/scripts/bash/setup-tasks.sh`) and
   writes `tasks.md` into the same `specs/<NNN-slug>/` directory.
2. Invoke the `speckit-analyze` skill. It runs only after `tasks.md` exists
   and checks `spec.md`, `plan.md` and `tasks.md` against each other for
   inconsistency, duplication, ambiguity and under-specification. Act on
   what it reports. Do not proceed to step 3 while it flags an inconsistency
   between the three artifacts.
3. Create `vault/40-outcomes/OUT-<today>-tasks-<slug>.md` from
   `vault/_templates/outcome.md` with `step: tasks` and `records:
   [$ARGUMENTS]`. Record what the analysis found and how it was resolved.
4. Leave the requirement's `status` unchanged — task breakdown is not a
   status-changing step in the ladder (`draft → specified → planned →
   tested → implemented → verified`).
5. Run `make graph && make validate`. Both must pass.
6. Commit with the requirement ID in the subject line.
