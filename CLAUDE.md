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
was written first, not the requirement's frontmatter alone. Note that a red
suite cannot be committed — `make validate` runs the suite for real and the
pre-commit hook runs `make validate` — so `tested` is recorded in the same
commit as the implementation, and the RED output in the outcome note is what
proves the tests came first. The rung is a
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
- **Correctness constraints need a test before they can advance** (PRD
  §13A.28's non-repainting tests and §41's anti-bias rules — no future
  leakage, look-ahead or repainting even if it improves the backtest —
  enforced as validator rule **R5**). A requirement flagged `hard_gated:
  true` in its frontmatter (currently the 6 `REQ-NRT-*` and 11 `REQ-BIAS-*`
  notes) cannot hold a status past `specified` without a linked test. This
  is the one validator rule that is never waived — write the test. The 14
  `REQ-PRIN-*` notes are also `type: constraint` (they restate PRD §0) but
  are deliberately not `hard_gated`: several restate PRD §0 process
  instructions (item 1: implement incrementally, by phases; item 14:
  correctness, replay parity and data integrity before performance
  optimization) — a paraphrase of the Ukrainian original, not a verbatim
  quote — that can never have a test, and gating them would only produce
  token tests.

  R5's coverage is narrower than PRD §0.13/§0.14 could support: the design
  intended it to also reach §35.3 (repaint regression) and §35.4 (future
  leak), but no requirement notes have been extracted for those sections
  yet, so today R5 only gates §13A.28 and §41. This is deferred requirement
  work, not a tooling bug — extract `REQ-*` notes for §35.3/§35.4 and flag
  them `hard_gated: true` when that work happens.

## Traceability

| Artifact | Carries |
|---|---|
| Requirement note | `id:` frontmatter in `vault/10-requirements/` |
| Requirement note (constraint) | `hard_gated: true/false` frontmatter, **required** on every `type: constraint` note — `collect_requirements` raises rather than defaulting a missing field to `false`, because a silent default there would let a note escape R5 just by omitting a line (see `vault/_templates/requirement.md`) |
| Spec Kit spec | `traces: [REQ-...]` frontmatter in `specs/<NNN-slug>/spec.md` |
| Test | `@pytest.mark.trace("REQ-...")` |
| Source file | `# @trace: REQ-...` (or `// @trace: REQ-...` for `.ts`/`.js`) |
| Outcome note | `records: [REQ-...]` frontmatter in `vault/40-outcomes/` |

`tools/trace/validate.py` checks seven rules over the graph (they are numbered
R1-R6 and R8; there is no R7):

| Rule | Fires when |
|---|---|
| R1 | status is `specified` or later, no spec `SPECIFIES` the requirement |
| R2 | status is `implemented` or later, no test `VERIFIES` the requirement |
| R3 | an edge names a requirement ID that doesn't exist as a node |
| R4 | status is past `draft`, no outcome note `RECORDS` the requirement |
| R5 | a `hard_gated: true` requirement is past `specified` with no test |
| R6 | a `depends_on` cycle among requirements |
| R8 | status is `implemented` or later, no git-tracked source file carries `# @trace: <id>` — or, for a roll-up requirement, some requirement in its `covers:` list has no such file ([[ADR-055]]) |

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
self-asserted, exactly like the `tested` rung above.

An `IMPLEMENTS` edge is required by exactly one rule, R8, and only from
`implemented` upwards: below that rung code links are advisory, and R3 merely
checks that one, if present, doesn't point at a nonexistent requirement. R8 is
what stopped a requirement reaching `implemented` with a full test suite and no
traceable code at all, which is how it was found.

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

Constraint notes derived from PRD §0 (`REQ-PRIN-*`) and §41 (`REQ-BIAS-*`)
carry their rule text as their `## Acceptance` verbatim, by design — the
prohibition itself is the checkable condition.

No note carries the `ACCEPTANCE-NOT-SPECIFIED` marker any more. Ten did: the
extractor writes it wherever a PRD section states deliverables and no acceptance
criteria, and it is what kept those notes in `draft`. `REQ-WP-016` left the list
on 2026-09-08, six `REQ-EXP-*` on 2026-09-09, and `REQ-PHASE-5`, `-6` and `-8`
on the same day. Every one of those criteria is **derived, not quoted**, and each
derivation names the PRD section behind each line — see
`docs/superpowers/specs/2026-09-08-cross-venue-acceptance-design.md`,
`…/2026-09-09-experiment-acceptance-design.md` and
`…/2026-09-09-phase-acceptance-design.md`. If the extractor is ever re-run over a
PRD section with no criteria, the marker comes back, and it means the same thing
it meant before.

The 11 `REQ-PHASE-*` notes also carry four lists in frontmatter: `covers:`
names the requirements that deliver the phase, and three name what it does not.
`not_delivered:` is work that remains and that this project can do;
`blocked:` waits on something outside this repository and **must name what**;
`deferred:` was decided against and **must name an ADR that exists**. They were
one list until [[REQ-WP-069]], which found Phase 4 unable to close however much
of it was finished, because two of its three entries were things nobody here
could do.

`tests/tools/trace/test_phase_coverage.py` checks `covers:` mechanically — every
covering requirement must exist and have reached `implemented` — checks that a
phase claiming to be `implemented` has an empty `not_delivered:`, and checks the
two costs above. Those costs are the point: without them, moving an entry from
one list to the next would close any phase at will. `REQ-PHASE-6` is `implemented` — the first to get there, on
2026-09-09, when `REQ-STORE-001` and `REQ-REPRO-001` closed its last two
deliverables. The other ten still have a non-empty list, which is why they are
`planned`.

## Commands

    make install     # venv (.venv, Python 3.12) + dependencies
    make up          # start the dev stack (postgres + minio); waits for healthy
    make down        # stop it; data volumes survive
    make reset       # stop it AND delete the volumes -- destructive
    make test        # pytest -q
    make lint        # ruff check + ruff format --check, over tools tests src
    make typecheck   # mypy --strict over src/
    make markers     # run the suite for real; dump @pytest.mark.trace links
                     # for tests that passed into .trace/tests.json
    make trace       # markers + rebuild .trace/graph.json
    make dashboard   # markers + rewrite the dashboard and notes' Trace sections
    make graph       # trace + dashboard
    make validate    # markers + check the seven coverage rules; exits 1 on violations
    make clean       # remove .trace, .pytest_cache, __pycache__

    make web-install    # npm ci in apps/web
    make web-typecheck  # tsc --noEmit
    make web-test       # vitest run
    make web-build      # vite build

A pre-commit hook runs `ruff` and `make validate` on every commit. Do not
bypass it with `--no-verify`; if it fails, fix the underlying gap.

## Two gates

The checks are split, because a requirement verified by an integration test
would otherwise make every commit depend on a running container runtime
(REQ-INFRA-002).

**Fast gate — the pre-commit hook, runs on every commit.** ruff check, ruff
format, and `make test-fast` (`pytest -m "not integration"`). Needs no services.
It is not the authority; it is the cheap check that catches most mistakes.

**Full gate — `.github/workflows/ci.yml`, runs on every push and pull request.**
Provisions PostgreSQL, MinIO and Node, then `make lint`, `make typecheck`,
`make test` (including integration), `make web-typecheck`, `make web-test`,
`make web-build` and `make validate`. Every step calls the same `make` target
you run locally, so the two cannot drift.

The three `web-*` steps run **only** in CI (ADR-021): `npm ci` on every commit
would need a Node toolchain for commits that touch no frontend file, breaking
the property REQ-INFRA-002 exists to protect. They are the clearest case of the
rule below — remove one from the workflow and that check runs nowhere.

**CI is where `implemented` is earned** for any requirement whose verification
needs a live service. A green local commit is not the same claim.

The rule that keeps this honest: **no check may be absent from both gates.** If
you remove something from `.pre-commit-config.yaml`, confirm it runs in the
workflow first. Run the full gate locally any time with `make validate` — it
still works, it just needs the stack up.

## Language

Artifacts — notes, specs, code, comments, commit messages — are in English.
Conversation with the user is in Ukrainian.
