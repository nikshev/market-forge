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
   right reason.
3. Set the requirement's `status: tested`, run `make graph && make validate`,
   and commit. `make graph` reads the markers via
   `tools.trace.pytest_plugin` (that's what `make markers` does under the
   hood) — the requirement is now provably covered before any implementation
   exists.
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
