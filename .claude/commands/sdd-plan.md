---
description: Plan a specified requirement through Spec Kit and record the outcome
argument-hint: <REQ-ID>
---

Plan `$ARGUMENTS`.

1. Confirm `vault/10-requirements/$ARGUMENTS.md` has `status: specified` (or
   later). If it is still `draft`, stop and say `/sdd-spec $ARGUMENTS` needs
   to run first.
2. Invoke the `speckit-plan` skill (it reads `.specify/memory/constitution.md`
   itself and evaluates the Constitution Check gates against the spec found
   through `.specify/scripts/bash/setup-plan.sh`). It writes the design
   artifacts — plan, research, data-model, contracts, quickstart — under the
   same `specs/<NNN-slug>/` directory as the spec.
3. Create `vault/40-outcomes/OUT-<today>-plan-<slug>.md` with `step: plan` and
   `records: [$ARGUMENTS]`. Record the approach chosen and what was rejected
   — not a summary of `plan.md`.
4. Check the requirement's `type` in its frontmatter:
   - If `type` is **not** `constraint`: set `status: planned`.
   - If `type` **is** `constraint`: rule R5 forbids this requirement from
     holding any status past `specified` without a linked test. Do not set
     `status: planned`. Instead write the failing test now — see
     `/sdd-implement` step 2 for the `@pytest.mark.trace("$ARGUMENTS")`
     marker convention — confirm it fails for the right reason, then set
     `status: tested` directly and say in your report why `planned` was
     skipped.
5. Run `make graph && make validate`. Both must pass.
6. Commit with the requirement ID in the subject line.
