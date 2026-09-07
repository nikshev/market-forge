---
traces: [REQ-INFRA-001]
status: draft
---

# Feature Specification: Deterministic Traceability Graph and Coverage Validator

**Feature Branch**: `001-traceability-tooling`

**Created**: 2026-09-07

**Status**: Draft

**Input**: Requirement REQ-INFRA-001 — "The repository holds a deterministic
graph linking the PRD to requirements, specs, tests and source, and a
validator that exits non-zero when a requirement's status outruns the
artifacts that justify it. Links are explicit and machine-checkable: `traces:`
frontmatter on specs, `@pytest.mark.trace(...)` on tests, `# @trace:` comments
in source. Nothing in the graph or the validator depends on a fuzzy or
LLM-derived edge."

**Note**: This spec is written retroactively, after `tools/trace/` already
existed (Tasks 4–10 of the SDD-traceability-infra plan). It documents what was
built, in Spec Kit's format, so REQ-INFRA-001 can be carried through the same
pipeline it describes. See REQ-INFRA-001's `## Notes` for why the ordering is
deliberate and not the pattern for future requirements.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A contributor checks whether a requirement is over-claimed (Priority: P1)

A contributor sets a requirement's `status:` to `implemented` and wants to
know, before committing, whether the claim is backed by a spec, a test and
code. They run `make validate`.

**Why this priority**: This is the entire point of the tool — a status change
that outruns its evidence must be caught mechanically, not by review
attention alone.

**Independent Test**: Set a requirement to `implemented` with no linked test,
run `make validate`, and confirm it exits 1 and names rule R2 and the
requirement's id.

**Acceptance Scenarios**:

1. **Given** a requirement at `implemented` with a spec, a verifying test and
   an implementing source file, **When** `make validate` runs, **Then** it
   exits 0.
2. **Given** the same requirement with its verifying test deleted, **When**
   `make validate` runs, **Then** it exits 1 and reports rule R2 against that
   requirement's id.

---

### User Story 2 - A contributor regenerates the dashboard without losing hand-written notes (Priority: P1)

A contributor edits a requirement note's `## Notes` section, then runs
`make graph`. The regenerated `## Trace` section must reflect the current
graph; every other section, including `## Notes`, must be byte-identical to
what they wrote.

**Why this priority**: A generator that silently destroys hand-written
content is worse than no generator — Tasks 1-12 were bitten by exactly this
once, which is why the rewrite is now guarded.

**Independent Test**: Run `make graph` twice in a row and confirm
`git status --short` reports no changes after the second run.

**Acceptance Scenarios**:

1. **Given** a requirement note with hand-written `## Notes` text, **When**
   the dashboard writer regenerates its `## Trace` section, **Then** every
   line outside that one section is unchanged.
2. **Given** a note whose prose happens to mention the generated-block marker
   text outside the actual marker pair, **When** the dashboard writer
   encounters it, **Then** it skips that note with a warning instead of
   guessing which occurrence is real.

---

### User Story 3 - A contributor traces one requirement end to end (Priority: P2)

A contributor wants to see, for one requirement id, exactly which spec, tests,
source files and outcome notes currently link to it.

**Why this priority**: Without a single-requirement view, "is this covered"
requires reading the whole dashboard by hand.

**Independent Test**: Run `.venv/bin/python -m tools.trace.cli show <ID>` and
confirm it lists the linked spec(s), test node ids, source file paths and
outcome note ids for that requirement alone.

**Acceptance Scenarios**:

1. **Given** a requirement with linked artifacts of every kind, **When**
   `show <ID>` runs, **Then** it prints all of them grouped by kind.
2. **Given** an id with no matching requirement node, **When** `show <ID>`
   runs, **Then** it exits with a usage error rather than an empty report.

### Edge Cases

- What happens when a parametrized test carries the trace marker? Each
  parametrized case is collected and counted individually, because links are
  read from pytest's own collection (`tools.trace.pytest_plugin`), not from
  static source parsing.
- What happens when two requirement notes declare the same `id:` in
  frontmatter? Graph construction raises `duplicate node id` and `make graph`
  fails hard rather than silently picking one.
- What happens when an edge names a requirement id that does not exist as a
  node (a typo in `traces:`, `depends_on`, or a trace comment)? Rule R3 reports
  it as a dangling reference rather than the graph build failing.
- What happens when `depends_on` edges form a cycle? Rule R6 reports the
  cycle; it is never silently broken by the graph builder.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST parse frontmatter and body from vault notes
  (requirements, specs, decisions, outcomes) into typed graph nodes.
- **FR-002**: The system MUST collect edges from four independent sources:
  spec `traces:` frontmatter (SPECIFIES), test collection markers
  (VERIFIES), source-comment markers (IMPLEMENTS), and outcome `records:`
  frontmatter (RECORDS) — plus `depends_on` (DEPENDS_ON) and decision
  `decides:` (DECIDES) frontmatter.
- **FR-003**: The system MUST read test-to-requirement links from pytest's
  own collection output, not from regexing test source, so parametrized and
  dynamically generated tests are counted per case.
- **FR-004**: The system MUST apply six coverage rules (R1-R6) over the
  assembled graph and return every violation, never just the first. A
  seventh rule, R7 (unique requirement ids), is enforced structurally by
  `TraceGraph.add` refusing a second node with an id already taken, rather
  than as a rule inside `validate.py`.
- **FR-005**: The system MUST exit non-zero exactly when at least one
  violation exists, and 0 otherwise (`tools.trace.cli validate`).
- **FR-006**: The system MUST regenerate the dashboard file and each
  requirement note's generated section without altering any text outside the
  matched marker pair, and MUST refuse to touch a file whose marker pair is
  not exactly one begin and one end, in the right order.
- **FR-007**: The system MUST provide a `show <ID>` command that prints
  exactly the artifacts linked to one requirement.
- **FR-008**: Rule R5 MUST fire for a `hard_gated: true` requirement past
  `specified` with no test, independent of R2, which only fires at
  `implemented` or later — a `planned` hard-gated requirement with no test
  must fail R5 while passing R2. (Scoped to `hard_gated` rather than to
  every `type: constraint` requirement so that constraint notes which can
  never have a test, such as the PRD §0 process principles, are not pinned
  below `implemented` forever.)
- **FR-009**: `make graph` MUST be idempotent: running it twice with no
  intervening change to source artifacts MUST leave the working tree clean.

### Key Entities

- **Node**: `id`, `kind` (requirement/spec/test/code/outcome/decision/PRD),
  `path`, `title`, free-form `attrs`.
- **Edge**: `src`, `dst`, `kind` (one of DERIVED_FROM, DEPENDS_ON, SPECIFIES,
  VERIFIES, IMPLEMENTS, RECORDS, DECIDES). Targets need not exist as nodes;
  rule R3 is what reports a dangling one.
- **Violation**: `rule` (R1-R6 — R7 never produces a `Violation`; it raises
  instead), `node_id`, `message` — the validator's only output shape.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `make validate` exits 0 on the repository as committed and 1
  the moment any one of R1-R7 is deliberately violated in a test fixture.
- **SC-002**: Every one of the six `validate.py` rules (R1-R6) has at least
  one passing and one failing unit test (`tests/tools/trace/test_validate.py`);
  R7 has a dedicated test asserting the raise
  (`test_r7_is_raised_by_the_graph_itself`).
- **SC-003**: Two consecutive runs of `make graph` produce an empty
  `git status --short`.
- **SC-004**: `tools.trace.cli show REQ-INFRA-001` prints its own spec, its
  five verifying tests, its eight implementing source files, and at least
  four recording outcome notes, once this feature's own implementation
  outcome is recorded — the tool proving itself against its own requirement.

## Assumptions

- The vault (`vault/10-requirements/`, `vault/40-outcomes/`,
  `vault/20-decisions/`) and `specs/<NNN-slug>/spec.md` are the only sources
  of graph data; there is no database or external store. `vault/30-specs/`
  notes exist only so specs are visible in Obsidian (see
  `.claude/commands/sdd-spec.md`) — no collector reads that directory, and
  the graph links a spec through the `traces:` field in
  `specs/<NNN-slug>/spec.md` instead.
- Requirement ids are permanent once assigned; the tool never renumbers or
  reuses one.
- `networkx` is an acceptable dependency for cycle detection (R6) and for the
  Mermaid/JSON exports.
