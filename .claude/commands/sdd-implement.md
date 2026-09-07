---
description: Implement a requirement test-first, with trace markers, and record the outcome
argument-hint: <REQ-ID>
---

Implement `$ARGUMENTS`.

1. Read `.specify/memory/constitution.md`. Principle I (no look-ahead, ever)
   and principle VII (live and replay are the same code) are not negotiable
   for market-data code.
2. Write the failing tests FIRST, in `tests/`. Every test that verifies this
   requirement carries the marker:

       @pytest.mark.trace("$ARGUMENTS")

   (registered in `pyproject.toml`'s `[tool.pytest.ini_options]`; multiple
   requirement IDs may be passed to one marker). Run
   `.venv/bin/python -m pytest -q` and confirm the new tests fail for the
   right reason. If the requirement instead annotates pre-existing,
   already-passing behavior (dogfooding the pipeline on its own tooling,
   for example), there is no red test to watch fail — skip this step's
   red-test cycle, mark the existing passing test(s), and say plainly in
   `tasks.md` and the outcome note that the step was skipped and why, rather
   than fabricating a failure that didn't happen.
3. Record the RED output — the command you ran and the failure, with enough of
   it to show the failure was for the right reason. This is the evidence that
   the tests came first, and it belongs in the outcome note from step 7.

   **Do not try to commit at this point.** `make validate` depends on
   `make markers`, which runs the suite for real, and the pre-commit hook runs
   `make validate` — so a red suite cannot be committed, by design. That is the
   property that stops a skipped test satisfying a coverage rule, and it is
   worth more than a separate `tested` commit.

   The consequence is that `status: tested` is recorded in the same commit as
   the implementation rather than ahead of it. The rung still means what it
   says — failing tests existed first — but the RED output is what proves it,
   not the commit order. Nothing mechanical reads `Status.TESTED`; see
   `CLAUDE.md` on the ladder being a discipline rather than a gate.
4. Invoke the `speckit-implement` skill. It reads `tasks.md` (via
   `.specify/scripts/bash/check-prerequisites.sh`) and executes the tasks in
   order.
5. Every source file you create or change to satisfy this requirement — under
   `src/` (create it if it doesn't exist yet) or `tools/` — carries a comment
   with the marker:

       # @trace: $ARGUMENTS

   (`// @trace: $ARGUMENTS` for `.ts`/`.tsx`/`.js`/`.jsx` files). One file may
   carry more than one marker if it satisfies more than one requirement; the
   collector recognizes each independently.
6. Run the full suite: `make test`. All tests pass.
7. Create `vault/40-outcomes/OUT-<today>-implement-<slug>.md` from
   `vault/_templates/outcome.md` with `step: implement`, `records:
   [$ARGUMENTS]`, and the commit hash once known (fill `commit:` after the
   commit in step 10, in a follow-up edit if needed).
8. Set the requirement's `status: implemented`.
9. Run `make graph && make validate`. Both must pass — rule R2 fails if a
   requirement reaches `implemented` with no linked test at all, which step 2
   already ruled out.
10. Commit with the requirement ID in the subject line.

Never set `status: verified`. That is a human judgement made after reading
the requirement against the PRD, not something this command decides.
