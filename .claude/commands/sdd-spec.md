---
description: Specify a requirement through Spec Kit and record the outcome
argument-hint: <REQ-ID>
---

Specify `$ARGUMENTS`.

1. Read `vault/10-requirements/$ARGUMENTS.md`. If its `## Acceptance` section
   contains the literal token `ACCEPTANCE-NOT-SPECIFIED`, **stop** and say so:
   this requirement has no PRD-backed acceptance criteria yet. Point at the
   note's `prd_ref` field, ask for the acceptance criteria to be written from
   that PRD section, and do not proceed until they are — an unspecified
   requirement cannot be specified.
2. Read `.specify/memory/constitution.md`. Every principle there applies;
   principle XIV ("Everything is traceable") is the one this whole command
   exists to satisfy.
3. Invoke the `speckit-specify` skill, passing the requirement's `##
   Requirement` and `## Acceptance` text as the feature description. It will
   create `specs/<NNN-slug>/spec.md` from the resolved spec template — the
   repository's override of that template
   (`.specify/templates/overrides/spec-template.md`) already carries a
   `traces: []` placeholder in its frontmatter, so the generated spec.md will
   already have the field; you only need to fill it in.
4. In the generated `specs/<NNN-slug>/spec.md`, set `traces: [$ARGUMENTS]`
   (add to the list rather than overwrite if other requirement IDs are
   already there).
5. Create `vault/30-specs/SPEC-<NNN-slug>.md` from `vault/_templates/spec.md`,
   with `requirement: $ARGUMENTS` and `speckit_path:
   specs/<NNN-slug>/spec.md`. This note exists only so the spec is visible in
   Obsidian — the trace graph itself links the spec through the `traces:`
   field in the Spec Kit spec.md from step 4, not through this note.
6. Create `vault/40-outcomes/OUT-<today>-spec-<slug>.md` from
   `vault/_templates/outcome.md` with `step: spec` and `records:
   [$ARGUMENTS]`. Record what was decided and what is still open in the
   `## What was decided` / `## What is still open` sections — not a summary
   of the spec.
7. Set the requirement's `status: specified`.
8. Run `make graph && make validate`. Both must pass — `make validate` will
   fail rule R1 if the `traces:` field from step 4 was missed or misspelled.
9. Commit with the requirement ID in the subject line.
