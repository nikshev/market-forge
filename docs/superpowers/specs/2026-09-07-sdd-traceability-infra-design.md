# Design: SDD + Traceability Infrastructure for market-forge

**Date:** 2026-09-07
**Status:** Approved (design), pending implementation plan
**Scope:** Infrastructure only. No ChannelFlow product code.

---

## 1. Purpose

`market-forge` implements ChannelFlow, described by a 7380-line Ukrainian PRD
(`channel_flow_prd_codex_ua_v5.md`): 51 sections, 8 phases, 20 work packages,
17 research experiments. The PRD's own instructions (§0) demand reproducibility
from request through test to commit hash, and forbid look-ahead / repainting
even when it would improve backtests.

That demand cannot be met by discipline alone across a project this size. This
design builds the machinery that enforces it:

1. **Spec-Driven Development** via GitHub Spec Kit (`specify-cli`), so every unit
   of work starts as a spec, not as code.
2. **An Obsidian vault** under git, where every requirement and every SDD step
   outcome is recorded as a note.
3. **A traceability graph** linking request → requirement → spec → test →
   implementation, with a validator that fails the build on gaps.
4. **Graphify** (`graphifyy`) indexing the repository for semantic queries over
   code and docs.

This design covers *only* that infrastructure. Phase 0 of the PRD (project
bootstrap, domain models) is the next iteration and will be specified through
the pipeline built here.

## 2. Non-goals

- No ChannelFlow product code: no connectors, bars, channels, signals, storage.
- No graph database (Neo4j / FalkorDB). File-backed graph only.
- No Claude Code hooks automation. Outcome capture runs through explicit slash
  commands plus a validator, so that what gets written stays reviewable.
- No GitHub Actions CI. The validator runs locally via `make validate` and a
  pre-commit hook. CI is added when the repository gets a remote worth gating.
- No web UI for the graph. Obsidian's own graph view plus a generated Mermaid
  dashboard is the interface.

## 3. Decisions taken

| Decision | Choice | Why |
|---|---|---|
| First slice | SDD infrastructure only | The pipeline must exist before it can carry Phase 0. |
| Vault location | `vault/` in-repo, committed | Notes version with the same commit hash as code and tests, which is what PRD §0.13 requires. |
| Trace mechanism | Explicit `@trace` markers + deterministic validator | Graphify's fuzzy index cannot prove coverage; a requirement with no test must be able to fail a build. |
| Requirement granularity | PRD's existing anchor entities | US-001..007, WP-001..020, EXP-001..017, Phase 0..8, plus acceptance criteria and anti-bias constraints. ~80–100 nodes with IDs that already exist in the PRD. |
| Outcome capture | Custom slash commands wrapping Spec Kit | Controlled, reviewable, no per-tool-call noise. |
| Artifact language | English | The PRD is Ukrainian but its technical vocabulary is already English; English matches better in Graphify's index and in code. Conversation stays Ukrainian. |
| Source of truth | Vault-as-hub | Keeps the vault a place a human can think in, rather than a generated mirror. |

## 4. Repository layout

```text
market-forge/
├── channel_flow_prd_codex_ua_v5.md   # request source of truth, unmodified
├── CLAUDE.md                         # SDD rules loaded into every session
├── Makefile                          # trace, validate, graph, index
├── pyproject.toml                    # trace tool + dev dependencies only
├── .python-version                   # 3.12
├── .gitignore
├── .pre-commit-config.yaml
├── .specify/                         # GitHub Spec Kit, integration: claude
├── .claude/
│   ├── settings.json                 # permissions for uv / graphify / make
│   └── commands/
│       ├── sdd-requirement.md
│       ├── sdd-spec.md
│       ├── sdd-plan.md
│       ├── sdd-tasks.md
│       ├── sdd-implement.md
│       └── sdd-trace.md
├── vault/
│   ├── .obsidian/                    # graph view config, templates plugin
│   ├── 00-index/
│   │   ├── Home.md
│   │   └── Traceability Dashboard.md # GENERATED, committed
│   ├── 10-requirements/  REQ-*.md
│   ├── 20-decisions/     ADR-*.md
│   ├── 30-specs/         SPEC-*.md   # vault-side notes linking to .specify
│   ├── 40-outcomes/      OUT-YYYY-MM-DD-<step>-<slug>.md
│   ├── 50-experiments/   EXP-*.md
│   └── _templates/       requirement.md, outcome.md, decision.md, spec.md
├── tools/
│   ├── trace/
│   │   ├── __init__.py
│   │   ├── model.py      # Node, Edge, Graph, Status dataclasses
│   │   ├── collect.py    # scan vault frontmatter, specs, pytest markers, code
│   │   ├── graph.py      # build networkx graph; export JSON + Mermaid
│   │   ├── validate.py   # coverage rules; returns violations
│   │   ├── dashboard.py  # render Traceability Dashboard.md
│   │   └── cli.py        # trace build | validate | show | dashboard
│   └── extract_prd.py    # one-shot PRD → REQ skeleton generator
├── tests/tools/trace/
│   ├── conftest.py       # fixture vault factory
│   ├── test_collect.py
│   ├── test_graph.py
│   ├── test_validate.py
│   └── test_dashboard.py
└── .trace/graph.json                 # GENERATED, gitignored
```

## 5. Requirement note format

One requirement per file in `vault/10-requirements/`, named `<id>.md`.

```markdown
---
id: REQ-US-001
title: Scan markets
type: user-story
prd_ref: "§4 US-001"
prd_lines: "251-254"
phase: 1
status: draft
depends_on: [REQ-WP-003, REQ-WP-005]
tags: [channel, scanning]
---

## Requirement

Statement in English, faithful to the PRD text. Where the PRD gives a formula,
threshold or state machine, it is reproduced here rather than paraphrased.

## Acceptance

- Observable, checkable conditions.

## Trace

<!-- trace:begin -->
- Spec: [[SPEC-004-market-scanner]]
- Tests: `tests/unit/test_scanner.py::test_universe_filter`
- Code: `src/channelflow/signals/engine.py`
<!-- trace:end -->

## Notes

Free-form. This section is human territory and is never machine-rewritten.
```

The `Trace` section is regenerated by `trace dashboard` from the graph, between
its `trace:begin` / `trace:end` markers. Everything else in the note, including
`Notes`, is written by hand and never machine-rewritten. A note whose `Trace`
section has no markers is left entirely alone and reported as a warning.

### 5.1 Field semantics

- **`id`** — `REQ-<KIND>-<NNN>`. Kinds mirror the PRD: `US`, `WP`, `EXP`,
  `PHASE`, `ACC` (acceptance criterion), `CON` (constraint / anti-bias rule),
  `INFRA` (this project's own tooling). IDs are permanent once created.
- **`type`** — one of `user-story`, `work-package`, `experiment`, `phase`,
  `acceptance`, `constraint`, `infrastructure`.
- **`prd_ref` / `prd_lines`** — anchor back to the request document. `prd_lines`
  is advisory; the PRD is not edited, so it stays valid, and a drift check is
  out of scope for v1.
- **`phase`** — PRD phase number, or `null` for cross-cutting constraints.
- **`status`** — ordered ladder: `draft` < `specified` < `planned` < `tested` <
  `implemented` < `verified`. Status is set by the SDD slash commands, and the
  validator checks that the artifacts each level claims actually exist.
  `tested` means failing tests exist and carry the marker; `implemented` means
  those tests pass. `verified` is set by hand only, and means a human confirmed
  the requirement against the PRD text; no command sets it, and the validator
  treats it exactly as `implemented`.
- **`depends_on`** — requirement IDs. Produces `DEPENDS_ON` edges. Cycles are a
  validator error.

## 6. Trace markers

Three marker forms, one per artifact kind. All three carry requirement IDs
verbatim, so they are greppable and machine-checkable.

**Tests** — a registered pytest marker:

```python
@pytest.mark.trace("REQ-US-001", "REQ-CON-003")
def test_channel_snapshot_never_mutates(): ...
```

Registered in `pyproject.toml` under `[tool.pytest.ini_options] markers`.
Collection uses `pytest --collect-only -q` with a small plugin that dumps
`(nodeid, marker args)` pairs to JSON, so the trace tool reads what pytest
actually resolved rather than re-parsing Python. This matters for
parametrized and dynamically generated tests.

**Code** — a line comment, one ID per marker, anywhere in the file:

```python
# @trace: REQ-US-001
```

Collected by line-based scan over `src/` and `tools/`, restricted to files
tracked by git.

**Specs** — Spec Kit spec files carry frontmatter:

```yaml
traces: [REQ-US-001, REQ-WP-003]
```

## 7. Graph model

Nodes, each with `id`, `kind`, `path`, and kind-specific attributes:

| Kind | Source |
|---|---|
| `request` | the PRD file, one node per referenced section |
| `requirement` | `vault/10-requirements/REQ-*.md` |
| `spec` | `.specify/specs/**` with a `traces:` field |
| `outcome` | `vault/40-outcomes/OUT-*.md` |
| `decision` | `vault/20-decisions/ADR-*.md` |
| `test` | one per pytest node id carrying a `trace` marker |
| `code` | one per source file containing `@trace:` comments |

Edges:

| Edge | From → To | Source |
|---|---|---|
| `DERIVED_FROM` | requirement → request | `prd_ref` |
| `DEPENDS_ON` | requirement → requirement | `depends_on` |
| `SPECIFIES` | spec → requirement | spec `traces:` |
| `VERIFIES` | test → requirement | pytest `trace` marker |
| `IMPLEMENTS` | code → requirement | `# @trace:` comment |
| `RECORDS` | outcome → requirement/spec | outcome frontmatter |
| `DECIDES` | decision → requirement | ADR frontmatter |

Outcome and decision notes carry the same frontmatter shape as requirements for
linking purposes:

```yaml
# vault/40-outcomes/OUT-2026-09-07-spec-infra-001.md
---
id: OUT-2026-09-07-spec-infra-001
step: spec          # requirement | spec | plan | tasks | implement
records: [REQ-INFRA-001]
commit: null        # filled with the commit hash once the step is committed
---
```

`records` produces the `RECORDS` edges. ADR notes use `decides: [REQ-...]`.

Built with `networkx`, which is already a `graphifyy` dependency, so it costs
nothing extra.

### 7.1 Outputs

- **`.trace/graph.json`** — full node/edge dump. Gitignored; rebuildable.
- **`vault/00-index/Traceability Dashboard.md`** — generated and **committed**:
  a coverage table (requirement, status, spec count, test count, code count) and
  a Mermaid subgraph per phase. Committed so gaps show up in PR diffs and in
  Obsidian without running anything.
- The dashboard writes only between `<!-- trace:begin -->` / `<!-- trace:end -->`
  markers, leaving any hand-written text in that file intact.

## 8. Validator rules

`make validate` → `trace validate`, exit 1 on any violation. Each rule reports
requirement ID, rule name, and what was missing.

1. **R1 — spec coverage.** `status >= specified` requires ≥1 `SPECIFIES` edge.
2. **R2 — test coverage.** `status >= implemented` requires ≥1 `VERIFIES` edge.
3. **R3 — no dangling markers.** Every ID in a pytest marker, `@trace:` comment,
   spec `traces:` list, or `depends_on` resolves to an existing requirement note.
4. **R4 — outcome recorded.** Every requirement whose status advanced past
   `draft` has ≥1 outcome note referencing it.
5. **R5 — correctness constraints are hard-gated.** Requirements of type
   `constraint` derived from PRD §13A.28 (non-repainting tests), §35.3 (repaint
   regression), §35.4 (future leak), and §41 (anti-bias rules) may not hold a
   status above `specified` without ≥1 `VERIFIES` edge. PRD §0.2 makes
   look-ahead non-negotiable, so this rule is not waivable by status alone.
6. **R6 — no dependency cycles** among `DEPENDS_ON` edges.
7. **R7 — unique IDs.** No two notes declare the same `id`.

Rules R1, R2, R4 and R5 are *status-gated*: a `draft` requirement with no spec
is fine, which is what lets ~100 requirements be extracted up front without
turning the build red.

## 9. Slash commands

Each writes an outcome note to `vault/40-outcomes/` and updates requirement
status. All are thin wrappers that delegate the actual SDD work to Spec Kit.

| Command | Does |
|---|---|
| `/sdd-requirement <PRD ref>` | Extracts a PRD section into a REQ note; assigns ID; links to request node. |
| `/sdd-spec <REQ-id>` | Runs Spec Kit `/specify`; adds `traces:` frontmatter; creates the vault spec note; sets status `specified`. |
| `/sdd-plan <REQ-id>` | Runs Spec Kit `/plan`; records outcome; sets status `planned`. |
| `/sdd-tasks <REQ-id>` | Runs Spec Kit `/tasks`; records outcome. |
| `/sdd-implement <REQ-id>` | Runs Spec Kit `/implement` under TDD; requires `@pytest.mark.trace` on new tests and `# @trace:` in new code; sets status `tested` then `implemented`. |
| `/sdd-trace [REQ-id]` | Rebuilds the graph, regenerates the dashboard, prints coverage gaps. |

## 10. Bootstrap sequence

1. Commit `channel_flow_prd_codex_ua_v5.md`, which is currently untracked. The
   request document must be in history before anything traces to it. In the
   same commit, record the removal of the TraceForge scaffold
   (`traceforge-init.sh`, `.traceforge/`), which is dropped deliberately: this
   design carries out the install itself, in steps 2-3 below. Rewrite
   `.gitignore` to cover `.venv/`, `.trace/`, `.graphify/` and `__pycache__/`,
   dropping the now-meaningless `.traceforge/` entries.
2. Create `.venv` on **Python 3.12**, not the system 3.14: the PRD targets
   3.12+, and `graphifyy` pulls ~25 tree-sitter packages whose 3.14 wheels are
   not guaranteed. If `uv` must download 3.12 into its cache, that is a change
   outside this folder and is confirmed with the user before it runs.
3. `uv pip install specify-cli graphifyy`. Exact `specify init` flags are
   verified against the installed version (1.0.4) rather than assumed; the
   integration target is `claude`.
4. Create the vault, `.obsidian` config, and note templates.
5. Build the trace tool **test-first**, per `superpowers:test-driven-development`.
6. Run `tools/extract_prd.py` to generate ~80–100 REQ skeletons, then review and
   fill acceptance criteria by hand. Generated skeletons land at `status: draft`.
7. Generate the dashboard; run the validator; it must pass.
8. **Dogfood.** Register the trace tool itself as `REQ-INFRA-001` and drive it
   through the full pipeline: `/sdd-spec` → `/sdd-plan` → `/sdd-tasks` →
   `/sdd-implement`. A pipeline that cannot carry its own tooling will not carry
   Phase 0.

Steps 1–4 are setup; 5–8 are the deliverable.

## 11. Testing

The trace tool is the only code this iteration produces, and it is tested first.

- **Fixture vault** (`conftest.py`): a factory building a temporary vault with
  requirements, specs, outcomes, test files and source files at chosen statuses.
- **`test_collect.py`** — frontmatter parsing, marker scanning, pytest marker
  extraction, malformed frontmatter, files without markers.
- **`test_graph.py`** — every edge kind is produced; JSON round-trips; Mermaid
  output is valid for an empty graph and a multi-phase graph.
- **`test_validate.py`** — one passing and one failing case per rule R1–R7.
  R5 gets its own case: a `constraint` requirement at `implemented` with no
  test must fail even when R2 would already catch it, so the rule is proven
  independent.
- **`test_dashboard.py`** — hand-written text outside the `trace:begin/end`
  markers survives regeneration; regeneration is idempotent.

`make validate` against the fixture vault must fail predictably, with the
violating requirement ID in the message.

## 12. Risks

- **`specify init --here` may overwrite or scaffold unexpectedly.** Run it
  before the vault and tool exist, inspect the diff, and commit separately so it
  can be reverted alone.
- **Graphify's index may be large or slow on a 191 KB PRD plus code.** It is
  gitignored and rebuildable, so worst case it is dropped without affecting the
  deterministic graph. The validator never depends on Graphify.
- **~100 hand-reviewed requirement notes is real work.** Extraction is scripted
  and skeletons start at `draft`, so the validator stays green while enrichment
  proceeds incrementally.
- **Python 3.12 may need downloading.** Confirmed with the user before it runs;
  if declined, fall back to whatever 3.12+ interpreter is already present and
  record the constraint.

## 13. Definition of done

- `.venv` with working `specify` and `graphify`; `.specify/` initialised.
- Vault exists with templates, index, and ~80–100 requirement notes.
- Trace tool passes its own test suite.
- `make trace && make validate` succeeds; the dashboard is generated and
  committed.
- `REQ-INFRA-001` has traversed the full SDD pipeline and reads `implemented`,
  with spec, plan, tasks, outcome notes, tests and code all linked in the graph.
- `CLAUDE.md` documents the loop so the next session follows it without being
  told.
