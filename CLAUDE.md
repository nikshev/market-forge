# market-forge

ChannelFlow: a crypto market-structure and signal radar. The PRD
(`channel_flow_prd_codex_ua_v5.md`, 7380 lines) is the source of truth and is
**read-only** — requirements quote it, nobody edits it, ever, for any reason.

## How work happens here

Every unit of work goes through spec-driven development and leaves a trace.
Six slash commands in `.claude/commands/` drive it; each wraps one or more of
Spec Kit's `speckit-*` skills (installed under `.claude/skills/`, invoked via
the Skill tool — there is no `/speckit.specify` dot-form) and adds exactly two
things the skill doesn't do on its own: an outcome note and a status
transition.

    /sdd-requirement <PRD ref>   → a REQ note in vault/10-requirements/
    /sdd-spec <REQ-ID>           → speckit-specify + outcome note, status: specified
    /sdd-plan <REQ-ID>           → speckit-plan + outcome note, status: planned
    /sdd-tasks <REQ-ID>          → speckit-tasks + speckit-analyze + outcome note
    /sdd-implement <REQ-ID>      → tests first, then speckit-implement, status: implemented
    /sdd-trace [REQ-ID]          → rebuild the graph, report gaps

Do not skip straight to code. Code without a `# @trace: REQ-...` comment
naming a real requirement has no place in the traceability graph, and
`make validate` will not see it — nor will it see a test without a matching
`@pytest.mark.trace("REQ-...")` marker.

## The rules that are not negotiable

`.specify/memory/constitution.md` holds fourteen governing principles:
I-XIII restate PRD §0, and XIV is this repository's own traceability rule.
Two catch people out most:

- **No look-ahead, ever** (Principle I). A feature computed at time `t` uses
  only data with `event_time <= t` that was actually available then. A
  better backtest is never a justification for looking further ahead.
- **Correctness constraints need a test before they can advance** (PRD §0.2 —
  no future leakage, look-ahead or repainting even if it improves the
  backtest — enforced as validator rule **R5**). A requirement whose `type`
  is `constraint` (anti-bias rules, non-repainting tests, PRD §0 principles
  themselves) cannot hold a status past `specified` without a linked test.
  This is the one validator rule that is never waived — write the test.

## Traceability

| Artifact | Carries |
|---|---|
| Requirement note | `id:` frontmatter in `vault/10-requirements/` |
| Spec Kit spec | `traces: [REQ-...]` frontmatter in `specs/<NNN-slug>/spec.md` |
| Test | `@pytest.mark.trace("REQ-...")` |
| Source file | `# @trace: REQ-...` (or `// @trace: REQ-...` for `.ts`/`.js`) |
| Outcome note | `records: [REQ-...]` frontmatter in `vault/40-outcomes/` |

`tools/trace/validate.py` checks six rules over the graph:

| Rule | Fires when |
|---|---|
| R1 | status is `specified` or later, no spec `SPECIFIES` the requirement |
| R2 | status is `implemented` or later, no test `VERIFIES` the requirement |
| R3 | an edge names a requirement ID that doesn't exist as a node |
| R4 | status is past `draft`, no outcome note `RECORDS` the requirement |
| R5 | a `constraint`-type requirement is past `specified` with no test |
| R6 | a `depends_on` cycle among requirements |

A duplicate `id:` across two requirement notes is caught earlier than this
table, while the graph is still being built (`TraceGraph.add` refuses the
second node) — it surfaces as `trace: cannot build graph: duplicate node id:
'<id>'` with exit 1, before any violation list is printed, not as a row in
the table above.

`make graph` rebuilds `.trace/graph.json` and regenerates the dashboard
(`vault/00-index/Traceability Dashboard.md`) and each requirement note's
`## Trace` section — but only the text between `<!-- trace:begin -->` and
`<!-- trace:end -->`. Everything outside those markers, in any file, is
hand-written and is never machine-rewritten; `tools/trace/dashboard.py`
requires exactly one marker pair per file it touches and refuses to guess
otherwise. Never add that marker pair to a requirement note anywhere except
its own `## Trace` section.

## Vault

`vault/` is hand-written, committed and authoritative. If a Graphify (or
similar) export of it ever appears under `graphify-out/obsidian/`, that copy
is generated and gitignored — never edit it and never cite it as a source;
regenerate it from `vault/` instead.

## Commands

    make install     # venv (.venv, Python 3.12) + dependencies
    make test        # pytest -q
    make lint        # ruff check tools tests
    make markers     # collect @pytest.mark.trace markers into .trace/tests.json
    make trace       # markers + rebuild .trace/graph.json
    make dashboard   # markers + rewrite the dashboard and notes' Trace sections
    make graph       # trace + dashboard
    make validate    # markers + check the six coverage rules; exits 1 on violations
    make clean       # remove .trace, .pytest_cache, __pycache__

A pre-commit hook runs `ruff` and `make validate` on every commit. Do not
bypass it with `--no-verify`; if it fails, fix the underlying gap.

## Language

Artifacts — notes, specs, code, comments, commit messages — are in English.
Conversation with the user is in Ukrainian.
