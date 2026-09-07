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
    /sdd-implement <REQ-ID>      → failing tests + commit (status: tested),
                                   then speckit-implement + commit (status: implemented)
    /sdd-trace [REQ-ID]          → rebuild the graph, report gaps

The status ladder is `draft → specified → planned → tested → implemented →
verified`. `/sdd-implement` passes through `tested` as its own commit,
*before* touching implementation code — that commit is what proves a test
was written first, not the requirement's frontmatter alone. The rung is a
discipline the commands follow, not a gate the tooling enforces: no
validator rule reads `status: tested` or checks that a requirement ever held
it. Rule R2 only requires a verifying test by the time status reaches
`implemented` — a requirement that jumped straight from `planned` to
`implemented` in one step, skipping the `tested` commit, would still pass
`make validate` today. Follow the rung anyway; the tooling not catching a
skip is a gap, not permission.

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
the table above. In practice two *requirement* notes can't reach that guard
in the first place: `_require_id` requires a note's `id:` to equal its own
filename stem, and two files can't share a stem in one directory, so a
copy-pasted frontmatter block that keeps the old `id:` fails first, and
earlier, as a filename mismatch — `trace: cannot build graph: <file>.md: id
'<id>' does not match filename '<stem>'`. The duplicate-node guard is real
and still runs, but what it would actually catch is two *different* kinds of
artifact colliding on one id (say a code file path and a test nodeid), not
two requirement notes.

A `VERIFIES` edge means the marked test **passed** the last time `make
markers` ran the suite for real — not that it merely exists, was collected,
or was skipped/xfailed. `make markers` runs `pytest` for real (not
`--collect-only`) for exactly this reason; a red suite makes `markers` fail
loudly with the failing tests printed, before `validate` ever runs, rather
than surfacing as a confusing R2/R5 violation. What `VERIFIES` still does not
mean: nothing checks that a `@pytest.mark.trace(...)` marker names a test
that genuinely exercises the requirement it claims to verify — that link is
self-asserted, exactly like the `tested` rung above. Nor is an `IMPLEMENTS`
edge required by any rule — R3 only checks that one, if present, doesn't
point at a nonexistent requirement — so code links are advisory: a
requirement can reach `implemented` with zero linked source files and
`make validate` will not notice.

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
    make lint        # ruff check + ruff format --check, tools tests
    make markers     # run the suite for real; dump @pytest.mark.trace links
                     # for tests that passed into .trace/tests.json
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
