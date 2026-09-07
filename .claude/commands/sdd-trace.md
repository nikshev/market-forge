---
description: Rebuild the traceability graph and report coverage gaps
argument-hint: [REQ-ID]
---

Rebuild the graph and report.

1. Run `make graph` (rebuilds `.trace/graph.json` via `tools.trace.cli build`,
   then regenerates `vault/00-index/Traceability Dashboard.md` and each
   requirement note's `## Trace` section via `tools.trace.cli dashboard` —
   only the text between `<!-- trace:begin -->` and `<!-- trace:end -->` is
   touched).

   If this step hard-fails instead of completing — printing
   `trace: cannot build graph: duplicate node id: '<id>'` and exiting 1,
   with no violation list at all — two requirement notes share the same
   `id:` in their frontmatter. Find both (`grep -rl "^id: <id>"
   vault/10-requirements/`) and fix whichever one was misnumbered. IDs are
   permanent once correctly assigned, so the fix is to correct the
   duplicate, not to renumber both.
2. Run `make validate` (`tools.trace.cli validate`; exits 1 if there are
   violations).
3. If `$ARGUMENTS` names a requirement, also run:

       .venv/bin/python -m tools.trace.cli show $ARGUMENTS

   to print exactly what specs, tests, code and outcomes currently link to
   it.
4. Report violations grouped by rule, with the shortest path to fixing each:
   - **R1** — the requirement's status is `specified` or later but no spec
     `SPECIFIES` edge points at it: run `/sdd-spec <ID>`.
   - **R2** — the requirement's status is `implemented` or later but no test
     `VERIFIES` edge points at it: write a test carrying
     `@pytest.mark.trace("<ID>")`.
   - **R3** — some edge (a `SPECIFIES`, `VERIFIES`, `IMPLEMENTS`, `RECORDS`,
     `DECIDES` or `DEPENDS_ON` edge) names a requirement ID that doesn't exist
     as a node: fix the typo in the referencing note/test/source comment, or
     create the missing requirement note.
   - **R4** — the requirement's status is past `draft` but no outcome note
     `RECORDS` it: create the missing `vault/40-outcomes/OUT-*.md` note for
     whichever `/sdd-*` step was actually done.
   - **R5** — a `constraint`-type requirement is past `specified` with no
     test. This is the one rule never to work around: PRD §0.2 makes it
     non-waivable — write the test.
   - **R6** — a `depends_on` cycle among requirements: break it by removing
     the weaker dependency edge, not by deleting the requirement.
5. If the dashboard or any requirement note's `## Trace` section changed,
   commit it — the pre-commit hook runs `make validate` again on that
   commit, so it must still be clean.
