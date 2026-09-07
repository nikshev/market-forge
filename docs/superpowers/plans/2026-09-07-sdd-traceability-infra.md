# SDD + Traceability Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the SDD pipeline for market-forge — Spec Kit, an in-repo Obsidian vault, and a deterministic request→requirement→spec→test→code trace graph whose validator fails the build on coverage gaps.

**Architecture:** Requirements are Markdown notes with YAML frontmatter in `vault/10-requirements/`. Specs, tests and source carry the requirement ID verbatim (`traces:` frontmatter, `@pytest.mark.trace(...)`, `# @trace:` comment). A small Python package walks those artifacts, builds a `networkx` graph, exports JSON plus a committed Markdown dashboard, and runs seven coverage rules. Graphify indexes the repo separately for semantic search and nothing depends on it.

**Tech Stack:** Python 3.12, `uv`, pytest, `networkx`, `PyYAML`, GitHub Spec Kit (`specify-cli` 1.0.4), Graphify (`graphifyy` 0.9.55), Obsidian.

**Spec:** `docs/superpowers/specs/2026-09-07-sdd-traceability-infra-design.md`

## Global Constraints

- **Python 3.12** exactly. `uv python list` shows `cpython-3.12.13` already in uv's cache; always pass `--no-python-downloads` so nothing is fetched.
- **Artifact language is English.** Notes, specs, code, comments, commit messages. Conversation with the user is Ukrainian.
- **Requirement ID grammar:** `REQ-<KIND>-<TOKEN>` where `KIND` is `[A-Z]+` and `TOKEN` is `[0-9A-Z]+`. Kinds in use: `US`, `WP`, `EXP`, `PHASE`, `PRIN`, `BIAS`, `NRT`, `INFRA`. `PHASE` tokens include letters (`REQ-PHASE-1A`), so never assume a zero-padded number.
- **Status ladder** is ordered: `draft` < `specified` < `planned` < `tested` < `implemented` < `verified`.
- **TDD is mandatory.** Every code task writes the failing test first, runs it to see it fail, then implements.
- **Never modify `channel_flow_prd_codex_ua_v5.md`.** It is the request source of truth and is read-only for the whole project.
- **The validator must not depend on Graphify.** Graphify is a semantic convenience; the deterministic graph stands alone.
- **All commands run from the repo root** `/Users/yevhenshkurnhykov/Work/my_projects/market-forge`, with `.venv` activated or via `uv run`.

---

## File Structure

| File | Responsibility |
|---|---|
| `tools/trace/model.py` | `Status`, `Node`, `Edge`, `TraceGraph` dataclasses. No I/O. |
| `tools/trace/frontmatter.py` | Split YAML frontmatter from Markdown body. No knowledge of requirements. |
| `tools/trace/collect.py` | Turn files on disk into `Node`/`Edge` lists. One collector per artifact kind. |
| `tools/trace/pytest_plugin.py` | Dump `(nodeid, requirement ids)` pairs during pytest collection. |
| `tools/trace/graph.py` | Assemble collectors into a `TraceGraph`; JSON and Mermaid export. |
| `tools/trace/validate.py` | Seven rules over a `TraceGraph`, returning `Violation`s. No printing. |
| `tools/trace/dashboard.py` | Render the dashboard and rewrite `Trace` sections between markers. |
| `tools/trace/cli.py` | argparse entry point: `build`, `validate`, `show`, `dashboard`. The only module that prints or exits. |
| `tools/extract_prd.py` | One-shot PRD → requirement skeleton generator. Not part of the runtime. |

Collectors are split from the graph so each can be tested against a fixture directory without building a graph, and the validator is split from the CLI so rules can be tested without capturing stdout.

---

## Task 1: Repository baseline

**Files:**
- Create: `pyproject.toml`, `.python-version`, `Makefile`, `tools/__init__.py`, `tools/trace/__init__.py`, `tests/__init__.py`, `tests/tools/__init__.py`, `tests/tools/trace/__init__.py`
- Modify: `.gitignore`
- Delete: `traceforge-init.sh`, `.traceforge/integrations.json`

**Interfaces:**
- Consumes: nothing.
- Produces: a working `.venv`, `uv run pytest` exiting 0, and `make` targets `venv`, `test`, `trace`, `validate` (the last two are stubs until Task 10).

- [ ] **Step 1: Commit the PRD and drop the TraceForge scaffold**

The PRD is currently untracked. Nothing may trace to a document that is not in history.

```bash
cd /Users/yevhenshkurnhykov/Work/my_projects/market-forge
cat > .gitignore <<'EOF'
.venv/
.trace/
graphify-out/
__pycache__/
*.py[cod]
.pytest_cache/
.DS_Store
EOF
git rm -q --cached --ignore-unmatch traceforge-init.sh .traceforge/integrations.json
rm -f traceforge-init.sh
rm -rf .traceforge
git add -A
git commit -m "Track the PRD as the request source of truth

The 7380-line ChannelFlow PRD is the document every requirement will trace
back to, so it belongs in history before the trace graph exists. The
TraceForge scaffold is removed: this project performs the specify/graphify
install directly."
```

- [ ] **Step 2: Create the virtual environment**

```bash
uv venv .venv --python 3.12 --no-python-downloads
.venv/bin/python --version
```

Expected: `Python 3.12.13`. If it reports anything else, stop — the rest of the plan assumes 3.12.

- [ ] **Step 3: Write `pyproject.toml`**

```toml
[project]
name = "market-forge-tools"
version = "0.1.0"
description = "Traceability tooling for the ChannelFlow project"
requires-python = ">=3.12,<3.13"
dependencies = [
    "networkx>=3.4",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.6",
    "pre-commit>=3.8",
]

[project.scripts]
trace = "tools.trace.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["tools*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "trace(*requirement_ids): link this test to one or more requirement IDs",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

Also write `.python-version`:

```text
3.12
```

- [ ] **Step 4: Create the package skeleton**

```bash
mkdir -p tools/trace tests/tools/trace
touch tools/__init__.py tools/trace/__init__.py
touch tests/__init__.py tests/tools/__init__.py tests/tools/trace/__init__.py
```

- [ ] **Step 5: Write the Makefile**

Note the literal tab indentation Make requires.

```makefile
VENV := .venv
PY   := $(VENV)/bin/python
PIP  := uv pip install --python $(PY)

.PHONY: venv install test lint trace validate dashboard graph clean

venv:
	uv venv $(VENV) --python 3.12 --no-python-downloads

install: venv
	$(PIP) -e ".[dev]"

test:
	$(PY) -m pytest -q

lint:
	$(VENV)/bin/ruff check tools tests

trace:
	$(PY) -m tools.trace.cli build

validate:
	$(PY) -m tools.trace.cli validate

dashboard:
	$(PY) -m tools.trace.cli dashboard

graph: trace dashboard

clean:
	rm -rf .trace .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
```

- [ ] **Step 6: Install and verify**

```bash
uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/python -m pytest -q
```

Expected: `no tests ran` and exit code 5 (pytest's "no tests collected"), not an import error. This confirms the package installs and pytest resolves `testpaths`.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .python-version Makefile tools tests
git commit -m "Add Python 3.12 tooling baseline

pyproject with the trace package, the registered 'trace' pytest marker,
ruff config, and a Makefile wrapping uv."
```

---

## Task 2: Spec Kit initialization, constitution, and spec template override

**Files:**
- Create: `.specify/` (generated), `.specify/memory/constitution.md`, `.specify/templates/overrides/spec-template.md`
- Modify: none

**Interfaces:**
- Consumes: the `.venv` from Task 1.
- Produces: `/speckit.*` slash commands in `.claude/commands/`, and every generated spec carrying a `traces:` frontmatter field.

- [ ] **Step 1: Install Spec Kit**

```bash
uv pip install --python .venv/bin/python specify-cli
.venv/bin/specify --version
```

Expected: version `1.0.4` or later.

- [ ] **Step 2: Initialize into this directory**

`--force` is required because the directory is not empty. Run it now, while the only files at risk are the PRD and `docs/`, and commit it alone so it can be reverted independently.

```bash
.venv/bin/specify init --here --force --non-interactive --integration claude
git status --short
```

Inspect the diff before committing. Expected new paths: `.specify/`, `.claude/commands/speckit.*.md`. If it touched `docs/` or the PRD, stop and report.

- [ ] **Step 3: Commit the scaffold on its own**

```bash
git add -A
git commit -m "Initialize GitHub Spec Kit with the claude integration

Committed alone so the scaffold can be reverted without touching
project code."
```

- [ ] **Step 4: Write the constitution from PRD §0**

Write `.specify/memory/constitution.md`. These are PRD §0's fourteen instructions, restated in English as governing principles. Every future spec inherits them.

```markdown
# ChannelFlow Constitution

The PRD (`channel_flow_prd_codex_ua_v5.md`) is the source of truth. These
principles are non-negotiable and apply to every spec, plan and implementation.

## I. No look-ahead, ever

Any feature computed at timestamp `t` uses only data with `event_time <= t`,
and only values that were actually available in real time at the moment of
decision. This holds even when violating it would improve a backtest.
A backtest improvement is never evidence that a leak is acceptable.

## II. Time is not one thing

`event_time`, `exchange_time`, `block_time`, `ingest_time`, `bar_open_time`
and `bar_close_time` are distinct and never conflated. Every model carrying a
timestamp names which one it holds.

## III. History is immutable

Finalized channel snapshots and signal snapshots are never rewritten. A
correction is a new record, not an edit.

## IV. Baselines before models

No ML or GMDH layer is added until deterministic baselines exist and leakage
tests pass. A model that cannot beat a deterministic baseline is not a result.

## V. Calibration, not accuracy

Any signal carrying a probabilistic score reports calibration metrics.
Accuracy alone is not an acceptable evaluation of a probability.

## VI. Every feature is documented

A feature declares its semantics, unit, cadence, source, freshness and leakage
policy. An undocumented feature is not done.

## VII. Live and replay are the same code

Code is deterministic in backtest mode and maximally identical between live
and replay. Divergence between the two is a defect, not a configuration.

## VIII. Connectors share one interface

Every new exchange or DEX connector implements the common canonical interface.

## IX. No automatic execution

Phases 1-3 form signals and alerts only. The system does not open positions.

## X. Thresholds are configuration

All numeric thresholds are configurable. Hard-coded trading thresholds are
forbidden outside test fixtures.

## XI. Results are reproducible

Every backtest and research result is reproducible from a versioned dataset,
config, code commit hash and model artifact hash.

## XII. Correctness precedes performance

Correctness, replay parity and data integrity are settled before any
performance optimization.

## XIII. Work is incremental

The system is built in the phases and against the acceptance criteria the PRD
defines, not ahead of them.

## XIV. Everything is traceable

Every unit of work carries a requirement ID from `vault/10-requirements/`
through spec, test and implementation. Work that cannot be traced is not done.
```

- [ ] **Step 5: Add the spec template override**

Spec Kit resolves templates top-down through a priority stack whose highest layer is `.specify/templates/overrides/`. Copy the core spec template and add the `traces:` field, so the field exists in every spec without anyone remembering it.

```bash
mkdir -p .specify/templates/overrides
cp .specify/templates/spec-template.md .specify/templates/overrides/spec-template.md
```

Then prepend this frontmatter block to `.specify/templates/overrides/spec-template.md`, above whatever the core template starts with:

```markdown
---
traces: []          # REQUIRED: requirement IDs from vault/10-requirements/, e.g. [REQ-WP-001]
status: draft
---

<!--
  `traces` is not optional. A spec with an empty `traces` list fails
  `make validate` under rule R1 as soon as its requirement leaves `draft`.
-->
```

If `.specify/templates/spec-template.md` does not exist under that exact name, list `.specify/templates/` and copy whichever file the `/speckit.specify` command reads; do not invent a filename.

- [ ] **Step 6: Verify the override is picked up**

```bash
ls -la .specify/templates/overrides/
head -20 .specify/templates/overrides/spec-template.md
```

Expected: the `traces: []` frontmatter is the first block in the file.

- [ ] **Step 7: Commit**

```bash
git add .specify/memory/constitution.md .specify/templates/overrides/
git commit -m "Add constitution from PRD section 0 and a traces-carrying spec template

PRD section 0's fourteen instructions become governing principles so they
enter every future spec automatically. The template override makes the
traces: frontmatter field unavoidable rather than remembered."
```

---

## Task 3: Obsidian vault skeleton

**Files:**
- Create: `vault/.obsidian/app.json`, `vault/.obsidian/graph.json`, `vault/00-index/Home.md`, `vault/00-index/Traceability Dashboard.md`, `vault/_templates/{requirement,outcome,decision,spec}.md`, `.gitkeep` in each empty content directory

**Interfaces:**
- Consumes: nothing.
- Produces: the directory layout the collectors in Task 5 walk, and the note templates every `/sdd-*` command fills.

- [ ] **Step 1: Create the directory tree**

```bash
mkdir -p vault/.obsidian vault/00-index vault/10-requirements vault/20-decisions \
         vault/30-specs vault/40-outcomes vault/50-experiments vault/_templates
touch vault/10-requirements/.gitkeep vault/20-decisions/.gitkeep \
      vault/30-specs/.gitkeep vault/40-outcomes/.gitkeep vault/50-experiments/.gitkeep
```

- [ ] **Step 2: Write the Obsidian config**

`vault/.obsidian/app.json` — turn off the features that would fight a git-backed vault:

```json
{
  "alwaysUpdateLinks": true,
  "newLinkFormat": "shortest",
  "useMarkdownLinks": false,
  "attachmentFolderPath": "_attachments",
  "showLineNumber": true,
  "strictLineBreaks": false
}
```

`vault/.obsidian/graph.json` — colour the graph by note kind so the trace layers are visible at a glance:

```json
{
  "collapse-filter": false,
  "search": "",
  "showTags": true,
  "showAttachments": false,
  "hideUnresolved": false,
  "showOrphans": true,
  "collapse-color-groups": false,
  "colorGroups": [
    { "query": "path:10-requirements", "color": { "a": 1, "rgb": 5431378 } },
    { "query": "path:30-specs",        "color": { "a": 1, "rgb": 14701138 } },
    { "query": "path:40-outcomes",     "color": { "a": 1, "rgb": 5789784 } },
    { "query": "path:20-decisions",    "color": { "a": 1, "rgb": 11621088 } },
    { "query": "path:50-experiments",  "color": { "a": 1, "rgb": 9819831 } }
  ],
  "collapse-display": false,
  "showArrow": true,
  "textFadeMultiplier": 0,
  "nodeSizeMultiplier": 1.2,
  "lineSizeMultiplier": 1,
  "collapse-forces": false,
  "centerStrength": 0.5,
  "repelStrength": 10,
  "linkStrength": 1,
  "linkDistance": 250,
  "scale": 1
}
```

- [ ] **Step 3: Write the four note templates**

`vault/_templates/requirement.md`:

```markdown
---
id: REQ-KIND-000
title: Short imperative title
type: user-story
prd_ref: "§N"
prd_lines: "0-0"
phase: null
status: draft
depends_on: []
tags: []
---

## Requirement

Faithful English statement. Where the PRD gives a formula, threshold or state
machine, reproduce it rather than paraphrasing it.

## Acceptance

- Observable, checkable condition.

## Trace

<!-- trace:begin -->
_Not yet generated. Run `make graph`._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
```

`vault/_templates/outcome.md`:

```markdown
---
id: OUT-YYYY-MM-DD-step-slug
step: spec
records: []
commit: null
---

## What was done

## What was decided

## What is still open
```

`vault/_templates/decision.md`:

```markdown
---
id: ADR-000
title: Short decision title
status: proposed
decides: []
date: YYYY-MM-DD
---

## Context

## Decision

## Consequences
```

`vault/_templates/spec.md`:

```markdown
---
id: SPEC-000-slug
requirement: REQ-KIND-000
speckit_path: specs/000-slug/spec.md
status: draft
---

## Summary

One paragraph. The authoritative text lives in the Spec Kit spec at
`speckit_path`; this note exists so the spec appears in the Obsidian graph.

## Links

- Requirement: [[REQ-KIND-000]]
```

- [ ] **Step 4: Write the vault index**

`vault/00-index/Home.md`:

```markdown
# market-forge Knowledge Vault

This vault is the record of how ChannelFlow gets built. It is committed to git,
so every note carries the same history as the code it describes.

## Layout

| Folder | Holds |
|---|---|
| `10-requirements/` | One note per requirement, extracted from the PRD. IDs are permanent. |
| `20-decisions/` | ADRs. Decisions that were not obvious and cost something. |
| `30-specs/` | One note per Spec Kit spec, so specs appear in the graph. |
| `40-outcomes/` | One note per SDD step. What happened, what was decided, what is open. |
| `50-experiments/` | PRD §39 research experiments and their results. |
| `_templates/` | Note templates. |

## Rules

- The PRD (`channel_flow_prd_codex_ua_v5.md`) is read-only. Requirements quote
  it; nobody edits it.
- Requirement IDs are permanent. Retire a requirement by setting its status,
  never by renumbering or deleting it.
- `Trace` sections are generated between `trace:begin`/`trace:end` markers.
  Everything else in a note is hand-written and is never machine-rewritten.
- `graphify-out/obsidian/` is a *different*, generated, gitignored vault. This
  one is authoritative.

## Entry points

- [[Traceability Dashboard]]
```

`vault/00-index/Traceability Dashboard.md`:

```markdown
# Traceability Dashboard

Generated by `make graph`. Do not edit between the markers.

<!-- trace:begin -->
_Not yet generated._
<!-- trace:end -->
```

- [ ] **Step 5: Commit**

```bash
git add vault
git commit -m "Add Obsidian vault skeleton with note templates

Committed in-repo so notes version with the code they describe, which is
what PRD section 0.13 requires of reproducible results."
```

---

## Task 4: Trace model and frontmatter parsing

**Files:**
- Create: `tools/trace/model.py`, `tools/trace/frontmatter.py`
- Test: `tests/tools/trace/test_model.py`, `tests/tools/trace/test_frontmatter.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Status` — `IntEnum` with `DRAFT=0, SPECIFIED=1, PLANNED=2, TESTED=3, IMPLEMENTED=4, VERIFIED=5` and `Status.parse(raw: str | None) -> Status`.
  - `Node(id: str, kind: str, path: str, title: str = "", attrs: dict = {})`, frozen.
  - `Edge(src: str, dst: str, kind: str)`, frozen.
  - `TraceGraph(nodes: dict[str, Node], edges: list[Edge])` with `add(node)`, `link(src, dst, kind)`, `nodes_of_kind(kind) -> list[Node]`, `edges_of_kind(kind) -> list[Edge]`, `edges_into(node_id, kind=None) -> list[Edge]`, `edges_out_of(node_id, kind=None) -> list[Edge]`.
  - `split_frontmatter(text: str) -> tuple[dict, str]`.

- [ ] **Step 1: Write the failing tests for the model**

`tests/tools/trace/test_model.py`:

```python
import pytest

from tools.trace.model import Edge, Node, Status, TraceGraph


def test_status_is_ordered():
    assert Status.DRAFT < Status.SPECIFIED < Status.PLANNED
    assert Status.PLANNED < Status.TESTED < Status.IMPLEMENTED < Status.VERIFIED


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("draft", Status.DRAFT),
        ("DRAFT", Status.DRAFT),
        ("  implemented  ", Status.IMPLEMENTED),
        (None, Status.DRAFT),
        ("", Status.DRAFT),
    ],
)
def test_status_parse_normalizes(raw, expected):
    assert Status.parse(raw) is expected


def test_status_parse_rejects_unknown():
    with pytest.raises(ValueError, match="unknown status: 'shipped'"):
        Status.parse("shipped")


def test_nodes_are_hashable_and_frozen():
    node = Node(id="REQ-US-001", kind="requirement", path="vault/10-requirements/REQ-US-001.md")
    assert {node}
    with pytest.raises(AttributeError):
        node.id = "REQ-US-002"


def test_add_and_lookup_by_kind():
    graph = TraceGraph()
    graph.add(Node(id="REQ-US-001", kind="requirement", path="a.md"))
    graph.add(Node(id="SPEC-001", kind="spec", path="specs/001-x/spec.md"))
    assert [n.id for n in graph.nodes_of_kind("requirement")] == ["REQ-US-001"]
    assert [n.id for n in graph.nodes_of_kind("spec")] == ["SPEC-001"]


def test_add_rejects_duplicate_ids():
    graph = TraceGraph()
    graph.add(Node(id="REQ-US-001", kind="requirement", path="a.md"))
    with pytest.raises(ValueError, match="duplicate node id: 'REQ-US-001'"):
        graph.add(Node(id="REQ-US-001", kind="requirement", path="b.md"))


def test_edges_into_and_out_of_filter_by_kind():
    graph = TraceGraph()
    graph.add(Node(id="REQ-US-001", kind="requirement", path="a.md"))
    graph.add(Node(id="SPEC-001", kind="spec", path="b.md"))
    graph.add(Node(id="t.py::test_x", kind="test", path="t.py"))
    graph.link("SPEC-001", "REQ-US-001", "SPECIFIES")
    graph.link("t.py::test_x", "REQ-US-001", "VERIFIES")

    assert len(graph.edges_into("REQ-US-001")) == 2
    assert graph.edges_into("REQ-US-001", "VERIFIES") == [
        Edge(src="t.py::test_x", dst="REQ-US-001", kind="VERIFIES")
    ]
    assert graph.edges_out_of("SPEC-001", "SPECIFIES")[0].dst == "REQ-US-001"
    assert graph.edges_out_of("REQ-US-001") == []


def test_link_allows_dangling_targets():
    # Dangling references are a validator finding (rule R3), not a crash here.
    graph = TraceGraph()
    graph.add(Node(id="SPEC-001", kind="spec", path="b.md"))
    graph.link("SPEC-001", "REQ-DOES-NOT-EXIST", "SPECIFIES")
    assert graph.edges_of_kind("SPECIFIES")[0].dst == "REQ-DOES-NOT-EXIST"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.trace.model'`

- [ ] **Step 3: Implement the model**

`tools/trace/model.py`:

```python
"""Value types for the traceability graph. No I/O lives here."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Status(IntEnum):
    """The requirement lifecycle, ordered so comparisons express the ladder."""

    DRAFT = 0
    SPECIFIED = 1
    PLANNED = 2
    TESTED = 3
    IMPLEMENTED = 4
    VERIFIED = 5

    @classmethod
    def parse(cls, raw: str | None) -> Status:
        if raw is None or not str(raw).strip():
            return cls.DRAFT
        key = str(raw).strip().upper()
        try:
            return cls[key]
        except KeyError:
            raise ValueError(f"unknown status: {str(raw).strip()!r}") from None


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    path: str
    title: str = ""
    attrs: dict = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str


@dataclass
class TraceGraph:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    def add(self, node: Node) -> None:
        if node.id in self.nodes:
            raise ValueError(f"duplicate node id: {node.id!r}")
        self.nodes[node.id] = node

    def link(self, src: str, dst: str, kind: str) -> None:
        """Record an edge. Targets need not exist; rule R3 reports dangling ones."""
        self.edges.append(Edge(src=src, dst=dst, kind=kind))

    def nodes_of_kind(self, kind: str) -> list[Node]:
        return [n for n in self.nodes.values() if n.kind == kind]

    def edges_of_kind(self, kind: str) -> list[Edge]:
        return [e for e in self.edges if e.kind == kind]

    def edges_into(self, node_id: str, kind: str | None = None) -> list[Edge]:
        return [e for e in self.edges if e.dst == node_id and (kind is None or e.kind == kind)]

    def edges_out_of(self, node_id: str, kind: str | None = None) -> list[Edge]:
        return [e for e in self.edges if e.src == node_id and (kind is None or e.kind == kind)]
```

`Node.attrs` is excluded from `compare`/`hash` so nodes stay hashable while carrying a mutable dict.

- [ ] **Step 4: Run the model tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_model.py -v`
Expected: PASS, 8 tests.

- [ ] **Step 5: Write the failing frontmatter tests**

`tests/tools/trace/test_frontmatter.py`:

```python
import pytest

from tools.trace.frontmatter import split_frontmatter

NOTE = """---
id: REQ-US-001
status: draft
depends_on: [REQ-WP-003]
---

## Requirement

Scan markets.
"""


def test_splits_metadata_from_body():
    meta, body = split_frontmatter(NOTE)
    assert meta["id"] == "REQ-US-001"
    assert meta["depends_on"] == ["REQ-WP-003"]
    assert body.startswith("\n## Requirement")


def test_missing_frontmatter_yields_empty_metadata():
    meta, body = split_frontmatter("# Just a heading\n")
    assert meta == {}
    assert body == "# Just a heading\n"


def test_unterminated_frontmatter_is_not_metadata():
    meta, body = split_frontmatter("---\nid: REQ-US-001\nno closing fence\n")
    assert meta == {}
    assert body.startswith("---")


def test_empty_frontmatter_block_yields_empty_metadata():
    meta, body = split_frontmatter("---\n---\nbody\n")
    assert meta == {}
    assert body == "body\n"


def test_malformed_yaml_raises_with_the_offending_text():
    with pytest.raises(ValueError, match="invalid YAML frontmatter"):
        split_frontmatter("---\nid: [unclosed\n---\nbody\n")


def test_non_mapping_frontmatter_raises():
    with pytest.raises(ValueError, match="frontmatter must be a mapping"):
        split_frontmatter("---\n- a\n- b\n---\nbody\n")


def test_leading_blank_lines_before_the_fence_are_tolerated():
    meta, _ = split_frontmatter("\n\n---\nid: REQ-US-002\n---\nbody\n")
    assert meta["id"] == "REQ-US-002"
```

- [ ] **Step 6: Run the frontmatter tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_frontmatter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.trace.frontmatter'`

- [ ] **Step 7: Implement frontmatter parsing**

`tools/trace/frontmatter.py`:

```python
"""Split YAML frontmatter from a Markdown body.

Knows nothing about requirements; it only understands the fence format.
"""

from __future__ import annotations

import yaml

FENCE = "---"


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (metadata, body).

    A document without a well-formed leading fence yields ({}, original text),
    so notes that were never meant to carry metadata pass through untouched.
    Malformed YAML inside a fence raises, because that is a typo worth failing on.
    """
    stripped = text.lstrip("\n")
    if not stripped.startswith(FENCE + "\n") and stripped.rstrip() != FENCE:
        return {}, text

    lines = stripped.split("\n")
    for index in range(1, len(lines)):
        if lines[index].rstrip() == FENCE:
            raw = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :])
            break
    else:
        return {}, text

    if not raw.strip():
        return {}, body

    try:
        meta = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML frontmatter: {exc}") from exc

    if meta is None:
        return {}, body
    if not isinstance(meta, dict):
        raise ValueError(f"frontmatter must be a mapping, got {type(meta).__name__}")
    return meta, body
```

- [ ] **Step 8: Run the frontmatter tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_frontmatter.py -v`
Expected: PASS, 7 tests.

- [ ] **Step 9: Commit**

```bash
git add tools/trace/model.py tools/trace/frontmatter.py \
        tests/tools/trace/test_model.py tests/tools/trace/test_frontmatter.py
git commit -m "Add trace graph value types and frontmatter parsing

Status is an IntEnum so the ladder is expressed by comparison rather than
by a lookup table. Dangling edges are allowed at the model level because
they are a validator finding, not a crash."
```

---

## Task 5: Collectors for vault notes, specs, and code markers

**Files:**
- Create: `tools/trace/collect.py`
- Test: `tests/tools/trace/conftest.py`, `tests/tools/trace/test_collect.py`

**Interfaces:**
- Consumes: `Node`, `Edge`, `Status`, `split_frontmatter` from Task 4.
- Produces, all returning `tuple[list[Node], list[Edge]]`:
  - `collect_requirements(vault_dir: Path)`
  - `collect_outcomes(vault_dir: Path)`
  - `collect_decisions(vault_dir: Path)`
  - `collect_specs(specs_dir: Path)`
  - `collect_code(roots: Sequence[Path])`
  - `collect_tests(dump_path: Path)` — reads the JSON the Task 6 plugin writes
  - and the constant `TRACE_COMMENT = re.compile(r"@trace:\s*(REQ-[A-Z]+-[0-9A-Z]+)")`
  - plus `PRD_NODE_ID = "PRD"`.

- [ ] **Step 1: Write the fixture vault factory**

`tests/tools/trace/conftest.py`:

```python
"""A factory for temporary vaults, so collector and validator tests share one shape."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


class VaultBuilder:
    def __init__(self, root: Path):
        self.root = root
        for sub in ("10-requirements", "20-decisions", "30-specs", "40-outcomes", "00-index"):
            (root / "vault" / sub).mkdir(parents=True, exist_ok=True)
        (root / "specs").mkdir(exist_ok=True)
        (root / "src").mkdir(exist_ok=True)

    @property
    def vault(self) -> Path:
        return self.root / "vault"

    @property
    def specs(self) -> Path:
        return self.root / "specs"

    def requirement(
        self,
        req_id: str,
        *,
        status: str = "draft",
        type_: str = "work-package",
        depends_on: list[str] | None = None,
        prd_ref: str = "§46",
        title: str = "A requirement",
    ) -> Path:
        deps = "[]" if not depends_on else "[" + ", ".join(depends_on) + "]"
        path = self.vault / "10-requirements" / f"{req_id}.md"
        path.write_text(
            textwrap.dedent(f"""\
                ---
                id: {req_id}
                title: {title}
                type: {type_}
                prd_ref: "{prd_ref}"
                phase: 0
                status: {status}
                depends_on: {deps}
                ---

                ## Requirement

                Body.

                ## Trace

                <!-- trace:begin -->
                _Not yet generated._
                <!-- trace:end -->

                ## Notes

                Hand-written, never machine-rewritten.
                """)
        )
        return path

    def spec(self, slug: str, traces: list[str]) -> Path:
        directory = self.specs / slug
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "spec.md"
        path.write_text(
            textwrap.dedent(f"""\
                ---
                traces: [{", ".join(traces)}]
                status: draft
                ---

                # Spec {slug}
                """)
        )
        return path

    def outcome(self, out_id: str, *, step: str, records: list[str]) -> Path:
        path = self.vault / "40-outcomes" / f"{out_id}.md"
        path.write_text(
            textwrap.dedent(f"""\
                ---
                id: {out_id}
                step: {step}
                records: [{", ".join(records)}]
                commit: null
                ---

                ## What was done
                """)
        )
        return path

    def decision(self, adr_id: str, decides: list[str]) -> Path:
        path = self.vault / "20-decisions" / f"{adr_id}.md"
        path.write_text(
            textwrap.dedent(f"""\
                ---
                id: {adr_id}
                title: A decision
                status: accepted
                decides: [{", ".join(decides)}]
                date: 2026-09-07
                ---

                ## Context
                """)
        )
        return path

    def source(self, relative: str, traces: list[str]) -> Path:
        path = self.root / "src" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        markers = "\n".join(f"# @trace: {t}" for t in traces)
        path.write_text(f'"""A module."""\n\n{markers}\n\n\ndef thing():\n    return 1\n')
        return path


@pytest.fixture
def vault(tmp_path: Path) -> VaultBuilder:
    return VaultBuilder(tmp_path)
```

- [ ] **Step 2: Write the failing collector tests**

`tests/tools/trace/test_collect.py`:

```python
import pytest

from tools.trace.collect import (
    PRD_NODE_ID,
    collect_code,
    collect_decisions,
    collect_outcomes,
    collect_requirements,
    collect_specs,
)


def test_collects_one_node_per_requirement(vault):
    vault.requirement("REQ-WP-001")
    vault.requirement("REQ-WP-002")
    nodes, _ = collect_requirements(vault.vault)
    assert sorted(n.id for n in nodes) == ["REQ-WP-001", "REQ-WP-002"]
    assert {n.kind for n in nodes} == {"requirement"}


def test_requirement_carries_status_and_type_in_attrs(vault):
    vault.requirement("REQ-WP-001", status="implemented", type_="work-package")
    nodes, _ = collect_requirements(vault.vault)
    assert nodes[0].attrs["status"] == "implemented"
    assert nodes[0].attrs["type"] == "work-package"


def test_requirement_links_back_to_the_prd(vault):
    vault.requirement("REQ-WP-001", prd_ref="§46 WP-001")
    _, edges = collect_requirements(vault.vault)
    derived = [(e.src, e.dst) for e in edges if e.kind == "DERIVED_FROM"]
    assert derived == [("REQ-WP-001", PRD_NODE_ID)]


def test_depends_on_becomes_edges(vault):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-002", "REQ-WP-003"])
    _, edges = collect_requirements(vault.vault)
    deps = sorted(e.dst for e in edges if e.kind == "DEPENDS_ON")
    assert deps == ["REQ-WP-002", "REQ-WP-003"]


def test_gitkeep_and_templates_are_ignored(vault):
    (vault.vault / "10-requirements" / ".gitkeep").write_text("")
    vault.requirement("REQ-WP-001")
    nodes, _ = collect_requirements(vault.vault)
    assert len(nodes) == 1


def test_requirement_without_an_id_field_raises_naming_the_file(vault):
    bad = vault.vault / "10-requirements" / "REQ-WP-009.md"
    bad.write_text("---\ntitle: no id here\n---\n\nbody\n")
    with pytest.raises(ValueError, match="REQ-WP-009.md: missing 'id'"):
        collect_requirements(vault.vault)


def test_requirement_id_must_match_its_filename(vault):
    bad = vault.vault / "10-requirements" / "REQ-WP-010.md"
    bad.write_text("---\nid: REQ-WP-999\n---\n\nbody\n")
    with pytest.raises(ValueError, match="id 'REQ-WP-999' does not match filename"):
        collect_requirements(vault.vault)


def test_specs_produce_specifies_edges(vault):
    vault.spec("001-bootstrap", ["REQ-WP-001", "REQ-WP-002"])
    nodes, edges = collect_specs(vault.specs)
    assert nodes[0].id == "SPEC-001-bootstrap"
    assert nodes[0].kind == "spec"
    assert sorted(e.dst for e in edges if e.kind == "SPECIFIES") == ["REQ-WP-001", "REQ-WP-002"]


def test_spec_with_empty_traces_yields_a_node_but_no_edges(vault):
    vault.spec("002-empty", [])
    nodes, edges = collect_specs(vault.specs)
    assert len(nodes) == 1
    assert edges == []


def test_outcomes_produce_records_edges(vault):
    vault.outcome("OUT-2026-09-07-spec-bootstrap", step="spec", records=["REQ-WP-001"])
    nodes, edges = collect_outcomes(vault.vault)
    assert nodes[0].kind == "outcome"
    assert nodes[0].attrs["step"] == "spec"
    assert [(e.src, e.dst, e.kind) for e in edges] == [
        ("OUT-2026-09-07-spec-bootstrap", "REQ-WP-001", "RECORDS")
    ]


def test_decisions_produce_decides_edges(vault):
    vault.decision("ADR-001", ["REQ-WP-001"])
    nodes, edges = collect_decisions(vault.vault)
    assert nodes[0].kind == "decision"
    assert [(e.src, e.dst, e.kind) for e in edges] == [("ADR-001", "REQ-WP-001", "DECIDES")]


def test_code_markers_produce_implements_edges(vault):
    vault.source("channelflow/bars.py", ["REQ-WP-005"])
    nodes, edges = collect_code([vault.root / "src"])
    assert nodes[0].kind == "code"
    assert nodes[0].id == "src/channelflow/bars.py"
    assert [(e.src, e.dst, e.kind) for e in edges] == [
        ("src/channelflow/bars.py", "REQ-WP-005", "IMPLEMENTS")
    ]


def test_a_file_with_two_markers_yields_one_node_and_two_edges(vault):
    vault.source("channelflow/channels.py", ["REQ-WP-006", "REQ-BIAS-002"])
    nodes, edges = collect_code([vault.root / "src"])
    assert len(nodes) == 1
    assert len(edges) == 2


def test_files_without_markers_produce_no_nodes(vault):
    (vault.root / "src" / "plain.py").write_text("def f():\n    return 1\n")
    nodes, edges = collect_code([vault.root / "src"])
    assert nodes == []
    assert edges == []


def test_code_collection_skips_pycache(vault):
    cache = vault.root / "src" / "__pycache__"
    cache.mkdir()
    (cache / "stale.py").write_text("# @trace: REQ-WP-001\n")
    nodes, _ = collect_code([vault.root / "src"])
    assert nodes == []
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_collect.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.trace.collect'`

- [ ] **Step 4: Implement the collectors**

`tools/trace/collect.py`:

```python
"""Turn files on disk into graph nodes and edges.

One collector per artifact kind. Every collector returns (nodes, edges) and
never touches the graph, so each can be tested against a directory alone.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path

from tools.trace.frontmatter import split_frontmatter
from tools.trace.model import Edge, Node

PRD_NODE_ID = "PRD"
REQ_ID = r"REQ-[A-Z]+-[0-9A-Z]+"
TRACE_COMMENT = re.compile(rf"@trace:\s*({REQ_ID})")

SKIP_DIRS = {"__pycache__", ".git", ".venv", "node_modules", ".pytest_cache"}
CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx"}


def _notes(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.md") if not p.name.startswith("."))


def _require_id(meta: dict, path: Path) -> str:
    node_id = meta.get("id")
    if not node_id:
        raise ValueError(f"{path.name}: missing 'id' in frontmatter")
    if node_id != path.stem:
        raise ValueError(f"{path.name}: id {node_id!r} does not match filename {path.stem!r}")
    return str(node_id)


def _id_list(meta: dict, field: str) -> list[str]:
    value = meta.get(field) or []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def collect_requirements(vault_dir: Path) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    for path in _notes(vault_dir / "10-requirements"):
        meta, _ = split_frontmatter(path.read_text())
        req_id = _require_id(meta, path)
        nodes.append(
            Node(
                id=req_id,
                kind="requirement",
                path=str(path),
                title=str(meta.get("title", "")),
                attrs={
                    "status": str(meta.get("status", "draft")),
                    "type": str(meta.get("type", "")),
                    "phase": meta.get("phase"),
                    "prd_ref": str(meta.get("prd_ref", "")),
                    "tags": _id_list(meta, "tags"),
                },
            )
        )
        edges.append(Edge(src=req_id, dst=PRD_NODE_ID, kind="DERIVED_FROM"))
        for dependency in _id_list(meta, "depends_on"):
            edges.append(Edge(src=req_id, dst=dependency, kind="DEPENDS_ON"))
    return nodes, edges


def collect_outcomes(vault_dir: Path) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    for path in _notes(vault_dir / "40-outcomes"):
        meta, _ = split_frontmatter(path.read_text())
        out_id = _require_id(meta, path)
        nodes.append(
            Node(
                id=out_id,
                kind="outcome",
                path=str(path),
                attrs={"step": str(meta.get("step", "")), "commit": meta.get("commit")},
            )
        )
        for target in _id_list(meta, "records"):
            edges.append(Edge(src=out_id, dst=target, kind="RECORDS"))
    return nodes, edges


def collect_decisions(vault_dir: Path) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    for path in _notes(vault_dir / "20-decisions"):
        meta, _ = split_frontmatter(path.read_text())
        adr_id = _require_id(meta, path)
        nodes.append(
            Node(
                id=adr_id,
                kind="decision",
                path=str(path),
                title=str(meta.get("title", "")),
                attrs={"status": str(meta.get("status", ""))},
            )
        )
        for target in _id_list(meta, "decides"):
            edges.append(Edge(src=adr_id, dst=target, kind="DECIDES"))
    return nodes, edges


def collect_specs(specs_dir: Path) -> tuple[list[Node], list[Edge]]:
    """Spec Kit writes specs/<NNN-slug>/spec.md; the node id is SPEC-<NNN-slug>."""
    nodes: list[Node] = []
    edges: list[Edge] = []
    if not specs_dir.is_dir():
        return nodes, edges
    for spec_path in sorted(specs_dir.glob("*/spec.md")):
        meta, _ = split_frontmatter(spec_path.read_text())
        spec_id = f"SPEC-{spec_path.parent.name}"
        nodes.append(
            Node(
                id=spec_id,
                kind="spec",
                path=str(spec_path),
                attrs={"status": str(meta.get("status", "draft"))},
            )
        )
        for target in _id_list(meta, "traces"):
            edges.append(Edge(src=spec_id, dst=target, kind="SPECIFIES"))
    return nodes, edges


def collect_code(roots: Sequence[Path]) -> tuple[list[Node], list[Edge]]:
    """One node per source file containing at least one `# @trace:` marker."""
    nodes: list[Node] = []
    edges: list[Edge] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in CODE_SUFFIXES:
                continue
            if SKIP_DIRS & set(path.parts):
                continue
            targets = TRACE_COMMENT.findall(path.read_text(errors="replace"))
            if not targets:
                continue
            file_id = str(path.relative_to(root.parent))
            nodes.append(Node(id=file_id, kind="code", path=file_id))
            for target in dict.fromkeys(targets):
                edges.append(Edge(src=file_id, dst=target, kind="IMPLEMENTS"))
    return nodes, edges


def collect_tests(dump_path: Path) -> tuple[list[Node], list[Edge]]:
    """Read the JSON written by tools.trace.pytest_plugin (see Task 6)."""
    nodes: list[Node] = []
    edges: list[Edge] = []
    if not dump_path.is_file():
        return nodes, edges
    for entry in json.loads(dump_path.read_text()):
        node_id = entry["nodeid"]
        nodes.append(Node(id=node_id, kind="test", path=node_id.split("::", 1)[0]))
        for target in dict.fromkeys(entry["requirements"]):
            edges.append(Edge(src=node_id, dst=target, kind="VERIFIES"))
    return nodes, edges
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_collect.py -v`
Expected: PASS, 15 tests.

- [ ] **Step 6: Commit**

```bash
git add tools/trace/collect.py tests/tools/trace/conftest.py tests/tools/trace/test_collect.py
git commit -m "Add collectors for requirements, specs, outcomes, decisions and code

Each collector returns (nodes, edges) and never touches the graph, so it
can be tested against a directory alone. A requirement whose id does not
match its filename is an error, because a silent mismatch would produce a
node nobody can find."
```

---

## Task 6: pytest plugin for test markers

**Files:**
- Create: `tools/trace/pytest_plugin.py`
- Test: `tests/tools/trace/test_pytest_plugin.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: a JSON file at the path given by `--trace-dump`, containing a list of `{"nodeid": str, "requirements": [str, ...]}`, sorted by `nodeid`. This is the input `collect_tests` reads.

Markers are read from pytest's own collection rather than by parsing Python source, so parametrized and dynamically generated tests are counted correctly.

- [ ] **Step 1: Write the failing test**

`tests/tools/trace/test_pytest_plugin.py`:

```python
import json

pytest_plugins = ["pytester"]


def test_dump_records_marked_tests(pytester):
    pytester.makepyfile(
        test_sample="""
        import pytest

        @pytest.mark.trace("REQ-WP-001")
        def test_one():
            pass

        @pytest.mark.trace("REQ-WP-002", "REQ-BIAS-003")
        def test_two():
            pass

        def test_unmarked():
            pass
        """
    )
    pytester.makeini("[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n")
    dump = pytester.path / "out" / "tests.json"

    result = pytester.runpytest(
        "-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "--collect-only", "-q"
    )
    result.ret  # collection only; exit code is not the assertion

    entries = json.loads(dump.read_text())
    by_id = {e["nodeid"].split("::")[-1]: e["requirements"] for e in entries}
    assert by_id == {
        "test_one": ["REQ-WP-001"],
        "test_two": ["REQ-WP-002", "REQ-BIAS-003"],
    }


def test_parametrized_tests_are_recorded_once_per_case(pytester):
    pytester.makepyfile(
        test_param="""
        import pytest

        @pytest.mark.trace("REQ-WP-004")
        @pytest.mark.parametrize("value", [1, 2, 3])
        def test_each(value):
            pass
        """
    )
    pytester.makeini("[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n")
    dump = pytester.path / "tests.json"

    pytester.runpytest("-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "--collect-only", "-q")

    entries = json.loads(dump.read_text())
    assert len(entries) == 3
    assert all(e["requirements"] == ["REQ-WP-004"] for e in entries)


def test_no_dump_option_writes_nothing(pytester):
    pytester.makepyfile(
        test_quiet="""
        import pytest

        @pytest.mark.trace("REQ-WP-001")
        def test_one():
            pass
        """
    )
    pytester.makeini("[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n")

    pytester.runpytest("-p", "tools.trace.pytest_plugin", "--collect-only", "-q")

    assert not (pytester.path / "tests.json").exists()


def test_dump_creates_missing_parent_directories(pytester):
    pytester.makepyfile(
        test_deep="""
        import pytest

        @pytest.mark.trace("REQ-WP-001")
        def test_one():
            pass
        """
    )
    pytester.makeini("[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n")
    dump = pytester.path / "a" / "b" / "tests.json"

    pytester.runpytest("-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "--collect-only", "-q")

    assert dump.is_file()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_pytest_plugin.py -v`
Expected: FAIL — pytest reports the plugin `tools.trace.pytest_plugin` cannot be imported.

- [ ] **Step 3: Implement the plugin**

`tools/trace/pytest_plugin.py`:

```python
"""Dump which tests claim which requirements, straight from pytest's collection.

Reading markers from collection rather than from source means parametrized and
dynamically generated tests are counted individually and correctly.

Usage:
    pytest -p tools.trace.pytest_plugin --trace-dump=.trace/tests.json --collect-only -q
"""

from __future__ import annotations

import json
from pathlib import Path


def pytest_addoption(parser) -> None:
    parser.addoption(
        "--trace-dump",
        action="store",
        default=None,
        metavar="PATH",
        help="Write collected @pytest.mark.trace requirement links to this JSON file.",
    )


def pytest_collection_finish(session) -> None:
    destination = session.config.getoption("--trace-dump")
    if not destination:
        return

    entries = []
    for item in session.items:
        requirements: list[str] = []
        for marker in item.iter_markers(name="trace"):
            requirements.extend(str(arg) for arg in marker.args)
        if requirements:
            entries.append(
                {"nodeid": item.nodeid, "requirements": list(dict.fromkeys(requirements))}
            )

    entries.sort(key=lambda entry: entry["nodeid"])
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_pytest_plugin.py -v`
Expected: PASS, 4 tests.

- [ ] **Step 5: Add the collector test that closes the loop**

Append to `tests/tools/trace/test_collect.py`:

```python
def test_collect_tests_reads_the_plugin_dump(vault, tmp_path):
    from tools.trace.collect import collect_tests

    dump = tmp_path / "tests.json"
    dump.write_text(
        '[{"nodeid": "tests/unit/test_bars.py::test_close", "requirements": ["REQ-WP-005"]}]'
    )
    nodes, edges = collect_tests(dump)
    assert nodes[0].kind == "test"
    assert nodes[0].path == "tests/unit/test_bars.py"
    assert [(e.src, e.dst, e.kind) for e in edges] == [
        ("tests/unit/test_bars.py::test_close", "REQ-WP-005", "VERIFIES")
    ]


def test_collect_tests_tolerates_a_missing_dump(tmp_path):
    from tools.trace.collect import collect_tests

    nodes, edges = collect_tests(tmp_path / "absent.json")
    assert (nodes, edges) == ([], [])
```

Run: `.venv/bin/python -m pytest tests/tools/trace/test_collect.py -v`
Expected: PASS, 17 tests.

- [ ] **Step 6: Commit**

```bash
git add tools/trace/pytest_plugin.py tests/tools/trace/test_pytest_plugin.py tests/tools/trace/test_collect.py
git commit -m "Collect test-to-requirement links from pytest collection

Reading markers from pytest rather than parsing source means parametrized
and dynamically generated tests are counted correctly."
```

---

## Task 7: Graph assembly and export

**Files:**
- Create: `tools/trace/graph.py`
- Test: `tests/tools/trace/test_graph.py`

**Interfaces:**
- Consumes: every collector from Tasks 5 and 6, plus `TraceGraph` from Task 4.
- Produces:
  - `build_graph(repo_root: Path, *, test_dump: Path | None = None) -> TraceGraph`
  - `to_dict(graph: TraceGraph) -> dict`
  - `write_json(graph: TraceGraph, path: Path) -> None`
  - `to_mermaid(graph: TraceGraph, *, phase: int | str | None = None) -> str`
  - `to_networkx(graph: TraceGraph) -> networkx.DiGraph`

- [ ] **Step 1: Write the failing tests**

`tests/tools/trace/test_graph.py`:

```python
import json

from tools.trace.collect import PRD_NODE_ID
from tools.trace.graph import build_graph, to_dict, to_mermaid, to_networkx, write_json


def test_build_graph_includes_the_prd_as_a_request_node(vault):
    vault.requirement("REQ-WP-001")
    graph = build_graph(vault.root)
    assert graph.nodes[PRD_NODE_ID].kind == "request"


def test_build_graph_wires_every_edge_kind(vault, tmp_path):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-002"])
    vault.requirement("REQ-WP-002")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.outcome("OUT-2026-09-07-spec-bootstrap", step="spec", records=["REQ-WP-001"])
    vault.decision("ADR-001", ["REQ-WP-001"])
    vault.source("channelflow/bars.py", ["REQ-WP-001"])
    dump = tmp_path / "tests.json"
    dump.write_text('[{"nodeid": "tests/test_a.py::test_x", "requirements": ["REQ-WP-001"]}]')

    graph = build_graph(vault.root, test_dump=dump)

    kinds = {e.kind for e in graph.edges}
    assert kinds == {
        "DERIVED_FROM",
        "DEPENDS_ON",
        "SPECIFIES",
        "RECORDS",
        "DECIDES",
        "IMPLEMENTS",
        "VERIFIES",
    }


def test_json_round_trips(vault, tmp_path):
    vault.requirement("REQ-WP-001")
    graph = build_graph(vault.root)
    out = tmp_path / "graph.json"
    write_json(graph, out)

    payload = json.loads(out.read_text())
    assert {n["id"] for n in payload["nodes"]} >= {"REQ-WP-001", PRD_NODE_ID}
    assert payload["edges"][0]["kind"] == "DERIVED_FROM"


def test_write_json_creates_missing_parents(vault, tmp_path):
    vault.requirement("REQ-WP-001")
    out = tmp_path / "deep" / "nested" / "graph.json"
    write_json(build_graph(vault.root), out)
    assert out.is_file()


def test_mermaid_of_an_empty_graph_is_still_valid(vault):
    graph = build_graph(vault.root)
    diagram = to_mermaid(graph)
    assert diagram.startswith("```mermaid\ngraph LR\n")
    assert diagram.rstrip().endswith("```")


def test_mermaid_escapes_quotes_in_titles(vault):
    vault.requirement("REQ-WP-001", title="A quoted title")
    (vault.vault / "10-requirements" / "REQ-WP-001.md").write_text(
        '---\nid: REQ-WP-001\ntitle: \'A "quoted" title\'\nstatus: draft\n---\n\nbody\n'
    )
    diagram = to_mermaid(build_graph(vault.root))
    label_line = next(line for line in diagram.split("\n") if line.strip().startswith("REQ_WP_001["))
    # Mermaid labels are double-quoted, so the label must carry exactly two quotes.
    assert label_line.count('"') == 2
    assert "'quoted'" in label_line


def test_networkx_export_preserves_counts(vault):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-002"])
    vault.requirement("REQ-WP-002")
    graph = build_graph(vault.root)
    digraph = to_networkx(graph)
    assert digraph.number_of_nodes() == len(graph.nodes)
    assert digraph.number_of_edges() == len(graph.edges)


def test_build_graph_is_deterministic(vault):
    vault.requirement("REQ-WP-002")
    vault.requirement("REQ-WP-001")
    first = to_dict(build_graph(vault.root))
    second = to_dict(build_graph(vault.root))
    assert first == second
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_graph.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.trace.graph'`

- [ ] **Step 3: Implement the graph module**

`tools/trace/graph.py`:

```python
"""Assemble collector output into one graph and export it."""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from tools.trace.collect import (
    PRD_NODE_ID,
    collect_code,
    collect_decisions,
    collect_outcomes,
    collect_requirements,
    collect_specs,
    collect_tests,
)
from tools.trace.model import Node, TraceGraph

PRD_FILENAME = "channel_flow_prd_codex_ua_v5.md"

EDGE_ARROWS = {
    "DERIVED_FROM": "-.->",
    "DEPENDS_ON": "-->",
    "SPECIFIES": "==>",
    "VERIFIES": "-->",
    "IMPLEMENTS": "-->",
    "RECORDS": "-.->",
    "DECIDES": "-.->",
}


def build_graph(repo_root: Path, *, test_dump: Path | None = None) -> TraceGraph:
    repo_root = Path(repo_root)
    graph = TraceGraph()
    graph.add(
        Node(
            id=PRD_NODE_ID,
            kind="request",
            path=PRD_FILENAME,
            title="ChannelFlow PRD",
        )
    )

    vault_dir = repo_root / "vault"
    collected = [
        collect_requirements(vault_dir),
        collect_outcomes(vault_dir),
        collect_decisions(vault_dir),
        collect_specs(repo_root / "specs"),
        collect_code([repo_root / "src", repo_root / "tools"]),
        collect_tests(test_dump or repo_root / ".trace" / "tests.json"),
    ]

    for nodes, edges in collected:
        for node in nodes:
            graph.add(node)
        for edge in edges:
            graph.link(edge.src, edge.dst, edge.kind)

    graph.edges.sort(key=lambda e: (e.kind, e.src, e.dst))
    return graph


def to_dict(graph: TraceGraph) -> dict:
    return {
        "nodes": [
            {
                "id": n.id,
                "kind": n.kind,
                "path": n.path,
                "title": n.title,
                "attrs": n.attrs,
            }
            for n in sorted(graph.nodes.values(), key=lambda n: (n.kind, n.id))
        ],
        "edges": [{"src": e.src, "dst": e.dst, "kind": e.kind} for e in graph.edges],
    }


def write_json(graph: TraceGraph, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_dict(graph), indent=2, sort_keys=False) + "\n")


def to_networkx(graph: TraceGraph) -> nx.DiGraph:
    digraph = nx.DiGraph()
    for node in graph.nodes.values():
        digraph.add_node(node.id, kind=node.kind, path=node.path, title=node.title, **node.attrs)
    for edge in graph.edges:
        digraph.add_edge(edge.src, edge.dst, kind=edge.kind)
    return digraph


def _label(node: Node) -> str:
    """Mermaid labels are quoted, so any inner quote must go."""
    text = f"{node.id}" if not node.title else f"{node.id}: {node.title}"
    return text.replace('"', "'").replace("[", "(").replace("]", ")")


def to_mermaid(graph: TraceGraph, *, phase: int | str | None = None) -> str:
    if phase is None:
        included = set(graph.nodes)
    else:
        requirements = {
            n.id
            for n in graph.nodes_of_kind("requirement")
            if str(n.attrs.get("phase")) == str(phase)
        }
        included = set(requirements)
        for edge in graph.edges:
            if edge.dst in requirements:
                included.add(edge.src)
            if edge.src in requirements:
                included.add(edge.dst)

    lines = ["```mermaid", "graph LR"]
    for node in sorted(graph.nodes.values(), key=lambda n: (n.kind, n.id)):
        if node.id not in included:
            continue
        lines.append(f'  {_safe(node.id)}["{_label(node)}"]')
    for edge in graph.edges:
        if edge.src not in included or edge.dst not in included:
            continue
        if edge.dst not in graph.nodes:
            continue
        arrow = EDGE_ARROWS.get(edge.kind, "-->")
        lines.append(f"  {_safe(edge.src)} {arrow}|{edge.kind}| {_safe(edge.dst)}")
    lines.append("```")
    return "\n".join(lines) + "\n"


def _safe(node_id: str) -> str:
    """Mermaid node ids may not contain ::, /, . or spaces."""
    return "".join(ch if ch.isalnum() else "_" for ch in node_id)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_graph.py -v`
Expected: PASS, 8 tests.

- [ ] **Step 5: Commit**

```bash
git add tools/trace/graph.py tests/tools/trace/test_graph.py
git commit -m "Assemble the trace graph and export JSON, Mermaid and networkx

Edges are sorted before export so two runs over the same tree produce
byte-identical output, which keeps the committed dashboard out of diffs
when nothing changed."
```

---

## Task 8: The validator

**Files:**
- Create: `tools/trace/validate.py`
- Test: `tests/tools/trace/test_validate.py`

**Interfaces:**
- Consumes: `TraceGraph`, `Status`, `PRD_NODE_ID`, `build_graph`.
- Produces:
  - `Violation(rule: str, node_id: str, message: str)`, frozen.
  - `validate(graph: TraceGraph) -> list[Violation]` — sorted by `(rule, node_id)`.
  - `CONSTRAINT_TYPES = frozenset({"constraint"})`.

Rules, restated from the spec so the implementer does not need the spec open:

| Rule | Fails when |
|---|---|
| R1 | A requirement at `specified` or higher has no incoming `SPECIFIES` edge. |
| R2 | A requirement at `implemented` or higher has no incoming `VERIFIES` edge. |
| R3 | Any edge points at a requirement ID that has no node. |
| R4 | A requirement above `draft` has no incoming `RECORDS` edge. |
| R5 | A requirement of type `constraint` is above `specified` with no incoming `VERIFIES` edge. |
| R6 | The `DEPENDS_ON` subgraph contains a cycle. |
| R7 | Two notes declare the same `id`. |

R7 is enforced by `TraceGraph.add` raising, so `validate` reports it only when a graph is constructed by other means; the CLI turns that exception into an R7 violation.

- [ ] **Step 1: Write the failing tests**

`tests/tools/trace/test_validate.py`:

```python
import pytest

from tools.trace.graph import build_graph
from tools.trace.model import Node, TraceGraph
from tools.trace.validate import Violation, validate


def rules(violations) -> set[str]:
    return {v.rule for v in violations}


# --- R1: spec coverage ---

def test_r1_passes_for_a_draft_requirement_without_a_spec(vault):
    vault.requirement("REQ-WP-001", status="draft")
    assert "R1" not in rules(validate(build_graph(vault.root)))


def test_r1_fails_for_a_specified_requirement_without_a_spec(vault):
    vault.requirement("REQ-WP-001", status="specified")
    vault.outcome("OUT-2026-09-07-spec-a", step="spec", records=["REQ-WP-001"])
    violations = validate(build_graph(vault.root))
    assert Violation(
        rule="R1",
        node_id="REQ-WP-001",
        message="status 'specified' requires at least one spec, found none",
    ) in violations


def test_r1_passes_once_a_spec_traces_it(vault):
    vault.requirement("REQ-WP-001", status="specified")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.outcome("OUT-2026-09-07-spec-a", step="spec", records=["REQ-WP-001"])
    assert "R1" not in rules(validate(build_graph(vault.root)))


# --- R2: test coverage ---

def test_r2_fails_for_an_implemented_requirement_without_a_test(vault):
    vault.requirement("REQ-WP-001", status="implemented")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.outcome("OUT-2026-09-07-impl-a", step="implement", records=["REQ-WP-001"])
    assert "R2" in rules(validate(build_graph(vault.root)))


def test_r2_passes_with_a_verifying_test(vault, tmp_path):
    vault.requirement("REQ-WP-001", status="implemented")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.outcome("OUT-2026-09-07-impl-a", step="implement", records=["REQ-WP-001"])
    dump = tmp_path / "tests.json"
    dump.write_text('[{"nodeid": "tests/test_a.py::test_x", "requirements": ["REQ-WP-001"]}]')
    assert "R2" not in rules(validate(build_graph(vault.root, test_dump=dump)))


# --- R3: dangling references ---

def test_r3_fails_on_a_spec_tracing_an_unknown_requirement(vault):
    vault.spec("001-bootstrap", ["REQ-WP-999"])
    violations = validate(build_graph(vault.root))
    assert any(v.rule == "R3" and "REQ-WP-999" in v.message for v in violations)


def test_r3_fails_on_a_depends_on_pointing_nowhere(vault):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-404"])
    violations = validate(build_graph(vault.root))
    assert any(v.rule == "R3" and "REQ-WP-404" in v.message for v in violations)


def test_r3_passes_when_every_reference_resolves(vault):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-002"])
    vault.requirement("REQ-WP-002")
    assert "R3" not in rules(validate(build_graph(vault.root)))


# --- R4: outcome recorded ---

def test_r4_fails_when_an_advanced_requirement_has_no_outcome(vault):
    vault.requirement("REQ-WP-001", status="specified")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    assert "R4" in rules(validate(build_graph(vault.root)))


def test_r4_passes_for_a_draft_requirement(vault):
    vault.requirement("REQ-WP-001", status="draft")
    assert "R4" not in rules(validate(build_graph(vault.root)))


# --- R5: correctness constraints are hard-gated ---

def test_r5_fails_for_a_planned_constraint_without_a_test(vault):
    """R5 bites where R2 does not: 'planned' is below 'implemented'."""
    vault.requirement("REQ-BIAS-002", status="planned", type_="constraint")
    vault.spec("001-no-centered-filters", ["REQ-BIAS-002"])
    vault.outcome("OUT-2026-09-07-plan-a", step="plan", records=["REQ-BIAS-002"])
    violations = validate(build_graph(vault.root))
    assert "R5" in rules(violations)
    assert "R2" not in rules(violations)


def test_r5_passes_for_a_specified_constraint_without_a_test(vault):
    vault.requirement("REQ-BIAS-002", status="specified", type_="constraint")
    vault.spec("001-no-centered-filters", ["REQ-BIAS-002"])
    vault.outcome("OUT-2026-09-07-spec-a", step="spec", records=["REQ-BIAS-002"])
    assert "R5" not in rules(validate(build_graph(vault.root)))


def test_r5_ignores_non_constraint_types(vault):
    vault.requirement("REQ-WP-001", status="planned", type_="work-package")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.outcome("OUT-2026-09-07-plan-a", step="plan", records=["REQ-WP-001"])
    assert "R5" not in rules(validate(build_graph(vault.root)))


# --- R6: dependency cycles ---

def test_r6_detects_a_two_node_cycle(vault):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-002"])
    vault.requirement("REQ-WP-002", depends_on=["REQ-WP-001"])
    violations = validate(build_graph(vault.root))
    assert "R6" in rules(violations)
    assert any("REQ-WP-001" in v.message and "REQ-WP-002" in v.message for v in violations)


def test_r6_passes_on_a_chain(vault):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-002"])
    vault.requirement("REQ-WP-002", depends_on=["REQ-WP-003"])
    vault.requirement("REQ-WP-003")
    assert "R6" not in rules(validate(build_graph(vault.root)))


# --- R7: unique ids ---

def test_r7_is_raised_by_the_graph_itself(vault):
    graph = TraceGraph()
    graph.add(Node(id="REQ-WP-001", kind="requirement", path="a.md"))
    with pytest.raises(ValueError, match="duplicate node id"):
        graph.add(Node(id="REQ-WP-001", kind="requirement", path="b.md"))


# --- ordering ---

def test_violations_are_sorted_by_rule_then_node(vault):
    vault.requirement("REQ-WP-002", status="specified")
    vault.requirement("REQ-WP-001", status="specified")
    violations = validate(build_graph(vault.root))
    keys = [(v.rule, v.node_id) for v in violations]
    assert keys == sorted(keys)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_validate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.trace.validate'`

- [ ] **Step 3: Implement the validator**

`tools/trace/validate.py`:

```python
"""Coverage rules over a trace graph. Returns findings; never prints or exits."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from tools.trace.model import Status, TraceGraph

CONSTRAINT_TYPES = frozenset({"constraint"})

# Edge kinds whose destination must be a requirement that exists.
REQUIREMENT_TARGETED = ("SPECIFIES", "VERIFIES", "IMPLEMENTS", "RECORDS", "DECIDES", "DEPENDS_ON")


@dataclass(frozen=True)
class Violation:
    rule: str
    node_id: str
    message: str


def validate(graph: TraceGraph) -> list[Violation]:
    found: list[Violation] = []
    requirements = {n.id: n for n in graph.nodes_of_kind("requirement")}

    for req_id, node in requirements.items():
        status = Status.parse(node.attrs.get("status"))
        req_type = str(node.attrs.get("type", ""))
        has_spec = bool(graph.edges_into(req_id, "SPECIFIES"))
        has_test = bool(graph.edges_into(req_id, "VERIFIES"))
        has_outcome = bool(graph.edges_into(req_id, "RECORDS"))
        label = str(status.name).lower()

        if status >= Status.SPECIFIED and not has_spec:
            found.append(
                Violation("R1", req_id, f"status {label!r} requires at least one spec, found none")
            )
        if status >= Status.IMPLEMENTED and not has_test:
            found.append(
                Violation("R2", req_id, f"status {label!r} requires at least one test, found none")
            )
        if status > Status.DRAFT and not has_outcome:
            found.append(
                Violation(
                    "R4", req_id, f"status {label!r} requires an outcome note, found none"
                )
            )
        if req_type in CONSTRAINT_TYPES and status > Status.SPECIFIED and not has_test:
            found.append(
                Violation(
                    "R5",
                    req_id,
                    f"correctness constraint at {label!r} has no test; PRD section 0.2 "
                    "makes this non-waivable",
                )
            )

    for edge in graph.edges:
        if edge.kind in REQUIREMENT_TARGETED and edge.dst not in requirements:
            found.append(
                Violation(
                    "R3",
                    edge.src,
                    f"{edge.kind} points at {edge.dst!r}, which is not a known requirement",
                )
            )

    found.extend(_cycles(graph))
    found.sort(key=lambda v: (v.rule, v.node_id, v.message))
    return found


def _cycles(graph: TraceGraph) -> list[Violation]:
    digraph = nx.DiGraph()
    for edge in graph.edges_of_kind("DEPENDS_ON"):
        digraph.add_edge(edge.src, edge.dst)
    violations: list[Violation] = []
    for cycle in nx.simple_cycles(digraph):
        ordered = sorted(cycle)
        violations.append(
            Violation("R6", ordered[0], "dependency cycle: " + " -> ".join(cycle + [cycle[0]]))
        )
    return violations
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_validate.py -v`
Expected: PASS, 17 tests.

- [ ] **Step 5: Commit**

```bash
git add tools/trace/validate.py tests/tools/trace/test_validate.py
git commit -m "Add the seven coverage rules

R5 is tested independently of R2: a constraint at 'planned' fails R5 while
passing R2, which proves the correctness gate is a real tightening rather
than a restatement."
```

---

## Task 9: Dashboard rendering and Trace-section regeneration

**Files:**
- Create: `tools/trace/dashboard.py`
- Test: `tests/tools/trace/test_dashboard.py`

**Interfaces:**
- Consumes: `TraceGraph`, `to_mermaid`, `Status`, `Violation`.
- Produces:
  - `BEGIN = "<!-- trace:begin -->"`, `END = "<!-- trace:end -->"`
  - `replace_between_markers(text: str, block: str) -> str` — raises `ValueError` if markers are missing or out of order.
  - `render_dashboard(graph: TraceGraph, violations: list[Violation]) -> str`
  - `write_dashboard(graph, violations, path: Path) -> None`
  - `render_requirement_trace(graph: TraceGraph, req_id: str) -> str`
  - `update_requirement_notes(graph: TraceGraph) -> tuple[list[Path], list[Path]]` — returns `(updated, skipped)`, where `skipped` holds notes with no marker pair.

- [ ] **Step 1: Write the failing tests**

`tests/tools/trace/test_dashboard.py`:

```python
import pytest

from tools.trace.dashboard import (
    BEGIN,
    END,
    render_dashboard,
    render_requirement_trace,
    replace_between_markers,
    update_requirement_notes,
    write_dashboard,
)
from tools.trace.graph import build_graph
from tools.trace.validate import validate


def test_replace_between_markers_keeps_surrounding_text():
    text = f"# Title\n\nIntro paragraph.\n\n{BEGIN}\nold\n{END}\n\nTrailing words.\n"
    result = replace_between_markers(text, "new content")
    assert "Intro paragraph." in result
    assert "Trailing words." in result
    assert "old" not in result
    assert "new content" in result


def test_replace_between_markers_is_idempotent():
    text = f"{BEGIN}\nold\n{END}\n"
    once = replace_between_markers(text, "new")
    twice = replace_between_markers(once, "new")
    assert once == twice


def test_replace_between_markers_rejects_a_missing_pair():
    with pytest.raises(ValueError, match="marker pair not found"):
        replace_between_markers("no markers here\n", "new")


def test_replace_between_markers_rejects_reversed_markers():
    with pytest.raises(ValueError, match="marker pair not found"):
        replace_between_markers(f"{END}\nx\n{BEGIN}\n", "new")


def test_dashboard_lists_every_requirement_with_counts(vault, tmp_path):
    vault.requirement("REQ-WP-001", status="specified")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.outcome("OUT-2026-09-07-spec-a", step="spec", records=["REQ-WP-001"])
    graph = build_graph(vault.root)
    text = render_dashboard(graph, validate(graph))
    assert "REQ-WP-001" in text
    assert "| specified |" in text


def test_dashboard_reports_violations(vault):
    vault.requirement("REQ-WP-001", status="specified")
    graph = build_graph(vault.root)
    text = render_dashboard(graph, validate(graph))
    assert "R1" in text
    assert "R4" in text


def test_dashboard_says_so_when_everything_passes(vault):
    vault.requirement("REQ-WP-001", status="draft")
    graph = build_graph(vault.root)
    text = render_dashboard(graph, validate(graph))
    assert "No violations." in text


def test_write_dashboard_preserves_handwritten_text(vault, tmp_path):
    target = tmp_path / "Traceability Dashboard.md"
    target.write_text(
        f"# Traceability Dashboard\n\nA hand-written preamble.\n\n{BEGIN}\nstale\n{END}\n"
    )
    vault.requirement("REQ-WP-001")
    graph = build_graph(vault.root)
    write_dashboard(graph, validate(graph), target)

    result = target.read_text()
    assert "A hand-written preamble." in result
    assert "stale" not in result
    assert "REQ-WP-001" in result


def test_requirement_trace_lists_linked_artifacts(vault, tmp_path):
    vault.requirement("REQ-WP-001", status="implemented")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.source("channelflow/bars.py", ["REQ-WP-001"])
    dump = tmp_path / "tests.json"
    dump.write_text('[{"nodeid": "tests/test_a.py::test_x", "requirements": ["REQ-WP-001"]}]')
    graph = build_graph(vault.root, test_dump=dump)

    block = render_requirement_trace(graph, "REQ-WP-001")
    assert "SPEC-001-bootstrap" in block
    assert "tests/test_a.py::test_x" in block
    assert "src/channelflow/bars.py" in block


def test_requirement_trace_says_none_when_nothing_links(vault):
    vault.requirement("REQ-WP-001")
    block = render_requirement_trace(build_graph(vault.root), "REQ-WP-001")
    assert "_No linked artifacts yet._" in block


def test_update_requirement_notes_preserves_the_notes_section(vault):
    vault.requirement("REQ-WP-001")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    graph = build_graph(vault.root)

    updated, skipped = update_requirement_notes(graph)

    assert skipped == []
    text = (vault.vault / "10-requirements" / "REQ-WP-001.md").read_text()
    assert "Hand-written, never machine-rewritten." in text
    assert "SPEC-001-bootstrap" in text
    assert len(updated) == 1


def test_update_requirement_notes_is_idempotent(vault):
    vault.requirement("REQ-WP-001")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    graph = build_graph(vault.root)
    path = vault.vault / "10-requirements" / "REQ-WP-001.md"

    update_requirement_notes(graph)
    once = path.read_text()
    update_requirement_notes(build_graph(vault.root))
    assert path.read_text() == once


def test_update_requirement_notes_skips_notes_without_markers(vault):
    path = vault.vault / "10-requirements" / "REQ-WP-001.md"
    path.write_text("---\nid: REQ-WP-001\nstatus: draft\n---\n\n## Requirement\n\nNo markers.\n")
    graph = build_graph(vault.root)

    updated, skipped = update_requirement_notes(graph)

    assert updated == []
    assert skipped == [path]
    assert "No markers." in path.read_text()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_dashboard.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.trace.dashboard'`

- [ ] **Step 3: Implement the dashboard**

`tools/trace/dashboard.py`:

```python
"""Render the traceability dashboard and refresh Trace sections in requirement notes.

Everything this module writes lives between marker comments. Text outside them
is hand-written and is never touched.
"""

from __future__ import annotations

from pathlib import Path

from tools.trace.graph import to_mermaid
from tools.trace.model import Status, TraceGraph
from tools.trace.validate import Violation

BEGIN = "<!-- trace:begin -->"
END = "<!-- trace:end -->"


def replace_between_markers(text: str, block: str) -> str:
    start = text.find(BEGIN)
    end = text.find(END)
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"marker pair not found: expected {BEGIN} before {END}")
    return text[: start + len(BEGIN)] + "\n" + block.rstrip("\n") + "\n" + text[end:]


def render_requirement_trace(graph: TraceGraph, req_id: str) -> str:
    specs = sorted(e.src for e in graph.edges_into(req_id, "SPECIFIES"))
    tests = sorted(e.src for e in graph.edges_into(req_id, "VERIFIES"))
    code = sorted(e.src for e in graph.edges_into(req_id, "IMPLEMENTS"))
    outcomes = sorted(e.src for e in graph.edges_into(req_id, "RECORDS"))

    if not (specs or tests or code or outcomes):
        return "_No linked artifacts yet._"

    lines: list[str] = []
    if specs:
        lines.append("- **Specs:** " + ", ".join(f"[[{s}]]" for s in specs))
    if tests:
        lines.append("- **Tests:**")
        lines.extend(f"    - `{t}`" for t in tests)
    if code:
        lines.append("- **Code:**")
        lines.extend(f"    - `{c}`" for c in code)
    if outcomes:
        lines.append("- **Outcomes:** " + ", ".join(f"[[{o}]]" for o in outcomes))
    return "\n".join(lines)


def update_requirement_notes(graph: TraceGraph) -> tuple[list[Path], list[Path]]:
    updated: list[Path] = []
    skipped: list[Path] = []
    for node in graph.nodes_of_kind("requirement"):
        path = Path(node.path)
        text = path.read_text()
        block = render_requirement_trace(graph, node.id)
        try:
            new_text = replace_between_markers(text, block)
        except ValueError:
            skipped.append(path)
            continue
        if new_text != text:
            path.write_text(new_text)
        updated.append(path)
    return updated, skipped


def render_dashboard(graph: TraceGraph, violations: list[Violation]) -> str:
    requirements = sorted(graph.nodes_of_kind("requirement"), key=lambda n: n.id)

    lines = ["## Coverage", ""]
    lines.append("| Requirement | Type | Phase | Status | Specs | Tests | Code |")
    lines.append("|---|---|---|---|---|---|---|")
    for node in requirements:
        status = Status.parse(node.attrs.get("status")).name.lower()
        lines.append(
            "| [[{id}]] | {type} | {phase} | {status} | {specs} | {tests} | {code} |".format(
                id=node.id,
                type=node.attrs.get("type", "") or "-",
                phase=node.attrs.get("phase") if node.attrs.get("phase") is not None else "-",
                status=status,
                specs=len(graph.edges_into(node.id, "SPECIFIES")),
                tests=len(graph.edges_into(node.id, "VERIFIES")),
                code=len(graph.edges_into(node.id, "IMPLEMENTS")),
            )
        )

    lines += ["", "## Violations", ""]
    if not violations:
        lines.append("No violations.")
    else:
        lines.append("| Rule | Node | Message |")
        lines.append("|---|---|---|")
        lines.extend(f"| {v.rule} | {v.node_id} | {v.message} |" for v in violations)

    phases = sorted(
        {str(n.attrs.get("phase")) for n in requirements if n.attrs.get("phase") is not None}
    )
    lines += ["", "## Graph", ""]
    if not phases:
        lines.append(to_mermaid(graph))
    else:
        for phase in phases:
            lines.append(f"### Phase {phase}")
            lines.append("")
            lines.append(to_mermaid(graph, phase=phase))
            lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def write_dashboard(graph: TraceGraph, violations: list[Violation], path: Path) -> None:
    path = Path(path)
    text = path.read_text()
    path.write_text(replace_between_markers(text, render_dashboard(graph, violations)))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_dashboard.py -v`
Expected: PASS, 13 tests.

- [ ] **Step 5: Commit**

```bash
git add tools/trace/dashboard.py tests/tools/trace/test_dashboard.py
git commit -m "Render the dashboard and refresh Trace sections in place

Writes only between marker comments, so the hand-written Notes section of
every requirement survives regeneration. A note with no markers is skipped
and reported rather than rewritten."
```

---

## Task 10: CLI, Makefile wiring, and pre-commit

**Files:**
- Create: `tools/trace/cli.py`, `.pre-commit-config.yaml`
- Modify: `Makefile`
- Test: `tests/tools/trace/test_cli.py`

**Interfaces:**
- Consumes: `build_graph`, `write_json`, `validate`, `write_dashboard`, `update_requirement_notes`.
- Produces: `main(argv: list[str] | None = None) -> int` with subcommands `build`, `validate`, `show <REQ-ID>`, `dashboard`, each accepting `--repo-root PATH`. Exit code 0 on success, 1 on violations, 2 on usage error.

- [ ] **Step 1: Write the failing tests**

`tests/tools/trace/test_cli.py`:

```python
import json

from tools.trace.cli import main


def test_build_writes_the_graph_json(vault, capsys):
    vault.requirement("REQ-WP-001")
    code = main(["build", "--repo-root", str(vault.root)])
    assert code == 0
    payload = json.loads((vault.root / ".trace" / "graph.json").read_text())
    assert any(n["id"] == "REQ-WP-001" for n in payload["nodes"])


def test_validate_exits_zero_when_clean(vault, capsys):
    vault.requirement("REQ-WP-001", status="draft")
    assert main(["validate", "--repo-root", str(vault.root)]) == 0
    assert "clean" in capsys.readouterr().out.lower()


def test_validate_exits_one_and_names_the_rule(vault, capsys):
    vault.requirement("REQ-WP-001", status="specified")
    code = main(["validate", "--repo-root", str(vault.root)])
    out = capsys.readouterr().out
    assert code == 1
    assert "R1" in out
    assert "REQ-WP-001" in out


def test_show_prints_the_linked_artifacts(vault, capsys):
    vault.requirement("REQ-WP-001")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    assert main(["show", "REQ-WP-001", "--repo-root", str(vault.root)]) == 0
    assert "SPEC-001-bootstrap" in capsys.readouterr().out


def test_show_of_an_unknown_requirement_exits_two(vault, capsys):
    code = main(["show", "REQ-WP-404", "--repo-root", str(vault.root)])
    assert code == 2
    assert "REQ-WP-404" in capsys.readouterr().err


def test_dashboard_updates_the_file_and_the_notes(vault):
    dashboard = vault.vault / "00-index" / "Traceability Dashboard.md"
    dashboard.write_text(
        "# Traceability Dashboard\n\n<!-- trace:begin -->\nstale\n<!-- trace:end -->\n"
    )
    vault.requirement("REQ-WP-001")
    vault.spec("001-bootstrap", ["REQ-WP-001"])

    assert main(["dashboard", "--repo-root", str(vault.root)]) == 0

    assert "REQ-WP-001" in dashboard.read_text()
    assert "SPEC-001-bootstrap" in (vault.vault / "10-requirements" / "REQ-WP-001.md").read_text()


def test_a_collector_error_exits_one_instead_of_raising(vault, capsys):
    """A malformed note must fail the build with a message, never a traceback."""
    vault.requirement("REQ-WP-001")
    (vault.vault / "10-requirements" / "REQ-WP-002.md").write_text(
        "---\nid: REQ-WP-001\nstatus: draft\n---\n\nbody\n"
    )
    code = main(["validate", "--repo-root", str(vault.root)])
    assert code == 1
    err = capsys.readouterr().err
    assert "cannot build graph" in err
    assert "REQ-WP-002.md" in err
```

Note: the last test's second file has `id: REQ-WP-001` in `REQ-WP-002.md`, which trips the filename-mismatch check in `collect_requirements` before it can trip R7. The CLI must turn that `ValueError` into a reported failure with exit code 1 rather than a traceback — that is what the test pins down.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.trace.cli'`

- [ ] **Step 3: Implement the CLI**

`tools/trace/cli.py`:

```python
"""Command line entry point. The only module here that prints or chooses exit codes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.trace.dashboard import render_requirement_trace, update_requirement_notes, write_dashboard
from tools.trace.graph import build_graph, write_json
from tools.trace.validate import validate

EXIT_OK = 0
EXIT_VIOLATIONS = 1
EXIT_USAGE = 2


def _parser() -> argparse.ArgumentParser:
    # --repo-root lives on a parent parser so it is accepted after the subcommand,
    # which is where it reads naturally: `trace validate --repo-root .`
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--repo-root", type=Path, default=Path.cwd(), help="Repository root (default: cwd)"
    )

    parser = argparse.ArgumentParser(prog="trace", description="ChannelFlow traceability graph")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", parents=[common], help="Rebuild .trace/graph.json")
    sub.add_parser("validate", parents=[common], help="Check coverage rules; exit 1 on violations")
    sub.add_parser(
        "dashboard", parents=[common], help="Regenerate the dashboard and requirement Trace sections"
    )
    show = sub.add_parser("show", parents=[common], help="Print what links to one requirement")
    show.add_argument("requirement", help="Requirement id, e.g. REQ-WP-001")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.repo_root)

    try:
        graph = build_graph(root)
    except ValueError as exc:
        print(f"trace: cannot build graph: {exc}", file=sys.stderr)
        return EXIT_VIOLATIONS

    if args.command == "build":
        target = root / ".trace" / "graph.json"
        write_json(graph, target)
        print(f"trace: wrote {target} ({len(graph.nodes)} nodes, {len(graph.edges)} edges)")
        return EXIT_OK

    if args.command == "validate":
        violations = validate(graph)
        if not violations:
            print(f"trace: clean ({len(graph.nodes)} nodes, {len(graph.edges)} edges)")
            return EXIT_OK
        for violation in violations:
            print(f"{violation.rule}  {violation.node_id}  {violation.message}")
        print(f"\ntrace: {len(violations)} violation(s)")
        return EXIT_VIOLATIONS

    if args.command == "dashboard":
        violations = validate(graph)
        dashboard_path = root / "vault" / "00-index" / "Traceability Dashboard.md"
        write_dashboard(graph, violations, dashboard_path)
        updated, skipped = update_requirement_notes(graph)
        print(f"trace: dashboard written, {len(updated)} requirement note(s) refreshed")
        for path in skipped:
            print(f"trace: warning: no trace markers in {path}", file=sys.stderr)
        return EXIT_OK

    if args.command == "show":
        if args.requirement not in graph.nodes:
            print(f"trace: unknown requirement {args.requirement!r}", file=sys.stderr)
            return EXIT_USAGE
        print(args.requirement)
        print(render_requirement_trace(graph, args.requirement))
        return EXIT_OK

    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/tools/trace/test_cli.py -v`
Expected: PASS, 7 tests.

- [ ] **Step 5: Wire the test-marker dump into the Makefile**

Replace the `trace`, `validate` and `dashboard` targets in `Makefile` so the graph always sees fresh test markers:

```makefile
.PHONY: markers
markers:
	$(PY) -m pytest -p tools.trace.pytest_plugin --trace-dump=.trace/tests.json \
	    --collect-only -q > /dev/null

trace: markers
	$(PY) -m tools.trace.cli build

validate: markers
	$(PY) -m tools.trace.cli validate

dashboard: markers
	$(PY) -m tools.trace.cli dashboard
```

- [ ] **Step 6: Add pre-commit**

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: trace-validate
        name: traceability coverage
        entry: .venv/bin/python -m tools.trace.cli validate
        language: system
        pass_filenames: false
        always_run: true
```

Install it:

```bash
.venv/bin/pre-commit install
```

- [ ] **Step 7: Verify the whole suite and the real repo**

```bash
.venv/bin/python -m pytest -q
make validate
```

Expected: all tests pass. `make validate` reports `trace: clean` — the vault has no requirements yet, so there is nothing to violate.

- [ ] **Step 8: Commit**

```bash
git add tools/trace/cli.py tests/tools/trace/test_cli.py Makefile .pre-commit-config.yaml
git commit -m "Add the trace CLI, Makefile wiring and a pre-commit coverage gate

Every trace target depends on a marker dump first, so the graph never
reports coverage from a stale test list."
```

---

## Task 11: Extract requirements from the PRD

**Files:**
- Create: `tools/extract_prd.py`, `vault/10-requirements/REQ-*.md` (86 notes)
- Test: `tests/tools/test_extract_prd.py`

**Interfaces:**
- Consumes: nothing from the trace package; it writes notes the collectors later read.
- Produces: `extract(prd_path: Path) -> list[Requirement]` and `write_notes(requirements, vault_dir) -> list[Path]`, where `Requirement` is a frozen dataclass with `id, title, type, prd_ref, prd_lines, phase, body`.

The six patterns below were verified against the actual PRD. Counts are exact: any deviation means the PRD changed and the script must be re-checked, not forced.

| Kind | Pattern | Count | Type |
|---|---|---|---|
| `US` | `^## US-(\d{3}) — (.+)$` | 7 | `user-story` |
| `WP` | `^## WP-(\d{3}) (.+)$` | 20 | `work-package` |
| `EXP` | `^## EXP-(\d{3}) (.+)$` | 17 | `experiment` |
| `PHASE` | `^#{2,3} Phase (\d[A-Z]?) — (.+)$` | 11 | `phase` |
| `NRT` | `^### Test ([A-F]) — (.+)$` | 6 | `constraint` |
| `BIAS` | `^(\d{1,2})\. (.+)$` within §41 | 11 | `constraint` |
| `PRIN` | `^(\d{1,2})\. (.+)$` within §0 | 14 | `constraint` |

- [ ] **Step 1: Write the failing test**

`tests/tools/test_extract_prd.py`:

```python
from pathlib import Path

import pytest

from tools.extract_prd import extract, write_notes

PRD = Path(__file__).resolve().parents[2] / "channel_flow_prd_codex_ua_v5.md"


@pytest.fixture(scope="module")
def requirements():
    return extract(PRD)


def test_extracts_the_expected_counts(requirements):
    counts: dict[str, int] = {}
    for req in requirements:
        counts[req.id.split("-")[1]] = counts.get(req.id.split("-")[1], 0) + 1
    assert counts == {
        "US": 7,
        "WP": 20,
        "EXP": 17,
        "PHASE": 11,
        "NRT": 6,
        "BIAS": 11,
        "PRIN": 14,
    }
    assert len(requirements) == 86


def test_ids_are_unique(requirements):
    ids = [r.id for r in requirements]
    assert len(ids) == len(set(ids))


def test_phase_ids_keep_their_letter_suffix(requirements):
    phase_ids = {r.id for r in requirements if r.id.startswith("REQ-PHASE-")}
    assert "REQ-PHASE-1A" in phase_ids
    assert "REQ-PHASE-7A" in phase_ids
    assert "REQ-PHASE-0" in phase_ids


def test_constraints_are_typed_as_constraints(requirements):
    for req in requirements:
        kind = req.id.split("-")[1]
        if kind in {"NRT", "BIAS", "PRIN"}:
            assert req.type == "constraint", req.id


def test_every_requirement_carries_a_prd_reference(requirements):
    for req in requirements:
        assert req.prd_ref, req.id
        assert req.prd_lines, req.id


def test_written_notes_are_collectable(requirements, tmp_path):
    from tools.trace.collect import collect_requirements

    vault_dir = tmp_path / "vault"
    (vault_dir / "10-requirements").mkdir(parents=True)
    written = write_notes(requirements, vault_dir)
    assert len(written) == 86

    nodes, edges = collect_requirements(vault_dir)
    assert len(nodes) == 86
    assert all(n.attrs["status"] == "draft" for n in nodes)


def test_written_notes_carry_trace_markers(requirements, tmp_path):
    vault_dir = tmp_path / "vault"
    (vault_dir / "10-requirements").mkdir(parents=True)
    written = write_notes(requirements[:1], vault_dir)
    text = written[0].read_text()
    assert "<!-- trace:begin -->" in text
    assert "<!-- trace:end -->" in text


def test_write_notes_refuses_to_clobber_an_existing_note(requirements, tmp_path):
    vault_dir = tmp_path / "vault"
    (vault_dir / "10-requirements").mkdir(parents=True)
    write_notes(requirements[:1], vault_dir)
    with pytest.raises(FileExistsError):
        write_notes(requirements[:1], vault_dir)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/tools/test_extract_prd.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.extract_prd'`

- [ ] **Step 3: Implement the extractor**

`tools/extract_prd.py`:

```python
"""One-shot generator: turn the PRD's anchor entities into requirement skeletons.

Not part of the runtime. Run once, review the output by hand, then enrich the
Acceptance sections. Refuses to overwrite an existing note, because requirement
IDs are permanent and hand-written prose must never be clobbered.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HEADING_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("US", re.compile(r"^## US-(\d{3}) — (.+)$"), "user-story"),
    ("WP", re.compile(r"^## WP-(\d{3}) (.+)$"), "work-package"),
    ("EXP", re.compile(r"^## EXP-(\d{3}) (.+)$"), "experiment"),
    ("PHASE", re.compile(r"^#{2,3} Phase (\d[A-Z]?) — (.+)$"), "phase"),
    ("NRT", re.compile(r"^### Test ([A-F]) — (.+)$"), "constraint"),
]

NUMBERED = re.compile(r"^(\d{1,2})\. (.+)$")
SECTION = re.compile(r"^#{1,3} .+$")

# Numbered-list blocks that become constraints, keyed by the heading that opens them.
NUMBERED_BLOCKS: list[tuple[str, str, str]] = [
    ("PRIN", "## 0. Інструкція для Codex", "§0"),
    ("BIAS", "# 41. Anti-Bias Rules", "§41"),
]


@dataclass(frozen=True)
class Requirement:
    id: str
    title: str
    type: str
    prd_ref: str
    prd_lines: str
    phase: str | None
    body: str


def _section_body(lines: list[str], start: int) -> tuple[str, int]:
    """Return the text under a heading, and the line index where it ends."""
    end = start + 1
    while end < len(lines) and not SECTION.match(lines[end]):
        end += 1
    return "\n".join(lines[start + 1 : end]).strip(), end


def extract(prd_path: Path) -> list[Requirement]:
    lines = Path(prd_path).read_text().split("\n")
    found: list[Requirement] = []

    for index, line in enumerate(lines):
        for kind, pattern, type_ in HEADING_PATTERNS:
            match = pattern.match(line)
            if not match:
                continue
            token, title = match.group(1), match.group(2).strip()
            body, end = _section_body(lines, index)
            phase = token if kind == "PHASE" else None
            found.append(
                Requirement(
                    id=f"REQ-{kind}-{token}",
                    title=title,
                    type=type_,
                    prd_ref=line.lstrip("# ").strip(),
                    prd_lines=f"{index + 1}-{end}",
                    phase=phase,
                    body=body,
                )
            )
            break

    for kind, heading, ref in NUMBERED_BLOCKS:
        try:
            start = lines.index(heading)
        except ValueError:
            raise ValueError(f"PRD heading not found: {heading!r}") from None
        _, end = _section_body(lines, start)
        counter = 0
        for offset in range(start + 1, end):
            match = NUMBERED.match(lines[offset].strip())
            if not match:
                continue
            counter += 1
            title = match.group(2).strip()
            found.append(
                Requirement(
                    id=f"REQ-{kind}-{counter:03d}",
                    title=title,
                    type="constraint",
                    prd_ref=ref,
                    prd_lines=f"{offset + 1}-{offset + 1}",
                    phase=None,
                    body=title,
                )
            )

    return found


NOTE_TEMPLATE = """---
id: {id}
title: {title}
type: {type}
prd_ref: "{prd_ref}"
prd_lines: "{prd_lines}"
phase: {phase}
status: draft
depends_on: []
tags: []
---

## Requirement

{body}

## Acceptance

- TO BE FILLED during review. A requirement with no acceptance criteria cannot
  leave `draft`.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
"""


def write_notes(requirements: list[Requirement], vault_dir: Path) -> list[Path]:
    target_dir = Path(vault_dir) / "10-requirements"
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for req in requirements:
        path = target_dir / f"{req.id}.md"
        if path.exists():
            raise FileExistsError(f"{path} already exists; requirement notes are never overwritten")
        path.write_text(
            NOTE_TEMPLATE.format(
                id=req.id,
                title=req.title.replace('"', "'"),
                type=req.type,
                prd_ref=req.prd_ref.replace('"', "'"),
                prd_lines=req.prd_lines,
                phase=req.phase if req.phase is not None else "null",
                body=req.body or req.title,
            )
        )
        written.append(path)
    return written


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    reqs = extract(root / "channel_flow_prd_codex_ua_v5.md")
    paths = write_notes(reqs, root / "vault")
    print(f"wrote {len(paths)} requirement notes")
```

Note the `Acceptance` placeholder text. That is deliberate and is the one place a
"to be filled" marker belongs: it is a data placeholder in generated content that
Step 6 replaces, not an instruction left in the plan.

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/python -m pytest tests/tools/test_extract_prd.py -v`
Expected: PASS, 8 tests. If the counts assertion fails, print what was found per kind and compare against the PRD before touching the expected numbers.

- [ ] **Step 5: Generate the notes**

```bash
.venv/bin/python -m tools.extract_prd
ls vault/10-requirements/*.md | wc -l
```

Expected: `86`.

- [ ] **Step 6: Review and enrich by hand**

Read every generated note. For each one:
- Replace the `TO BE FILLED` acceptance placeholder with the observable conditions the PRD states. Where the PRD's phase section gives explicit "Acceptance:" bullets, copy them.
- Fill `depends_on` where the PRD makes a dependency explicit (for example `REQ-WP-004` order book service depends on `REQ-WP-003` Binance connector).
- Translate any Ukrainian body text to English, keeping formulas and thresholds verbatim.

This is the slowest step in the plan. Work through it in batches of ten notes with a commit per batch, so review stays reviewable.

- [ ] **Step 7: Build the graph and check it is clean**

```bash
make graph
make validate
git diff --stat
```

Expected: `trace: clean`. Every requirement is at `draft`, so R1, R2, R4 and R5 are all status-gated off. R3 must pass, which proves every `depends_on` you filled in resolves to a real note. R6 must pass, which proves you introduced no dependency cycles.

- [ ] **Step 8: Commit**

```bash
git add tools/extract_prd.py tests/tools/test_extract_prd.py vault/
git commit -m "Extract 86 requirements from the PRD into the vault

Seven user stories, twenty work packages, seventeen experiments, eleven
phases, six non-repainting tests, eleven anti-bias rules and fourteen
constitutional principles. All at draft; acceptance criteria filled by
hand against the PRD text."
```

---

## Task 12: SDD slash commands and CLAUDE.md

**Files:**
- Create: `.claude/commands/sdd-requirement.md`, `sdd-spec.md`, `sdd-plan.md`, `sdd-tasks.md`, `sdd-implement.md`, `sdd-trace.md`, `CLAUDE.md`

**Interfaces:**
- Consumes: the `/speckit.*` commands from Task 2, the `trace` CLI from Task 10, the vault templates from Task 3.
- Produces: the workflow every future session follows.

Each `/sdd-*` command adds exactly two things to its `/speckit.*` counterpart: an outcome note, and a status transition. It never reimplements what Spec Kit does.

- [ ] **Step 1: Write `.claude/commands/sdd-requirement.md`**

```markdown
---
description: Extract a PRD section into a new requirement note in the vault
argument-hint: <PRD section reference, e.g. "§13.2" or "WP-021">
---

Create a requirement note from the PRD section `$ARGUMENTS`.

1. Read the named section of `channel_flow_prd_codex_ua_v5.md`. Never modify it.
2. Choose an ID: `REQ-<KIND>-<TOKEN>`. Reuse an existing kind (`US`, `WP`, `EXP`,
   `PHASE`, `PRIN`, `BIAS`, `NRT`, `INFRA`) unless none fits. Check
   `vault/10-requirements/` for the next free token. IDs are permanent.
3. Copy `vault/_templates/requirement.md` to `vault/10-requirements/<ID>.md` and
   fill it. Write the Requirement section in English, reproducing formulas,
   thresholds and state machines verbatim rather than paraphrasing them.
4. Fill `Acceptance` with observable conditions. A requirement with no
   acceptance criteria may not leave `draft`.
5. Set `depends_on` for any requirement this one genuinely needs first.
6. Leave `status: draft`.
7. Run `make graph && make validate`. Both must pass before you report done.
```

- [ ] **Step 2: Write `.claude/commands/sdd-spec.md`**

```markdown
---
description: Specify a requirement through Spec Kit and record the outcome
argument-hint: <REQ-ID>
---

Specify `$ARGUMENTS`.

1. Read `vault/10-requirements/$ARGUMENTS.md`. If its `Acceptance` section is
   empty or still says TO BE FILLED, stop and say so — an unspecified
   requirement cannot be specified.
2. Read `.specify/memory/constitution.md`. Every principle there applies.
3. Run `/speckit.specify` with the requirement's text as the input.
4. In the generated `specs/<NNN-slug>/spec.md`, set `traces: [$ARGUMENTS]`.
5. Create `vault/30-specs/SPEC-<NNN-slug>.md` from `vault/_templates/spec.md`.
6. Create `vault/40-outcomes/OUT-<today>-spec-<slug>.md` from
   `vault/_templates/outcome.md` with `step: spec` and `records: [$ARGUMENTS]`.
   Record what was decided and what is still open — not a summary of the spec.
7. Set the requirement's `status: specified`.
8. Run `make graph && make validate`. Both must pass.
9. Commit with the requirement ID in the subject line.
```

- [ ] **Step 3: Write `.claude/commands/sdd-plan.md`**

```markdown
---
description: Plan a specified requirement through Spec Kit and record the outcome
argument-hint: <REQ-ID>
---

Plan `$ARGUMENTS`.

1. Confirm the requirement's status is `specified`. If not, stop and say which
   step is missing.
2. Run `/speckit.plan`.
3. Create `vault/40-outcomes/OUT-<today>-plan-<slug>.md` with `step: plan` and
   `records: [$ARGUMENTS]`. Record the approach chosen and what was rejected.
4. Set the requirement's `status: planned`.

   Exception: if the requirement's `type` is `constraint`, it may not enter
   `planned` without a test — rule R5. Write the failing test first, set
   `status: tested`, and say why you skipped `planned`.
5. Run `make graph && make validate`. Both must pass.
6. Commit with the requirement ID in the subject line.
```

- [ ] **Step 4: Write `.claude/commands/sdd-tasks.md`**

```markdown
---
description: Break a planned requirement into tasks and check cross-artifact consistency
argument-hint: <REQ-ID>
---

Break down `$ARGUMENTS`.

1. Run `/speckit.tasks`.
2. Run `/speckit.analyze` and act on what it reports. Do not proceed while it
   flags an inconsistency between the spec, the plan and the tasks.
3. Create `vault/40-outcomes/OUT-<today>-tasks-<slug>.md` with `step: tasks` and
   `records: [$ARGUMENTS]`.
4. Leave the status unchanged.
5. Run `make graph && make validate`. Both must pass.
6. Commit with the requirement ID in the subject line.
```

- [ ] **Step 5: Write `.claude/commands/sdd-implement.md`**

```markdown
---
description: Implement a requirement test-first, with trace markers, and record the outcome
argument-hint: <REQ-ID>
---

Implement `$ARGUMENTS`.

1. Read `.specify/memory/constitution.md`. Principle I (no look-ahead) and
   principle VII (live/replay parity) are not negotiable for market data code.
2. Write the failing tests FIRST. Every test carries the marker:

       @pytest.mark.trace("$ARGUMENTS")

   Run them and confirm they fail for the right reason.
3. Set the requirement's `status: tested`, run `make graph && make validate`,
   and commit. The requirement is now provably covered before any
   implementation exists.
4. Run `/speckit.implement`.
5. Every source file you create or change to satisfy this requirement carries:

       # @trace: $ARGUMENTS

6. Run the full suite. All tests pass.
7. Create `vault/40-outcomes/OUT-<today>-implement-<slug>.md` with
   `step: implement`, `records: [$ARGUMENTS]`, and the commit hash once known.
8. Set the requirement's `status: implemented`.
9. Run `make graph && make validate`. Both must pass.
10. Commit with the requirement ID in the subject line.

Never set `status: verified`. That is a human judgement made after reading the
requirement against the PRD.
```

- [ ] **Step 6: Write `.claude/commands/sdd-trace.md`**

```markdown
---
description: Rebuild the traceability graph and report coverage gaps
argument-hint: [REQ-ID]
---

Rebuild the graph and report.

1. Run `make graph`.
2. Run `make validate`.
3. If `$ARGUMENTS` names a requirement, also run:

       .venv/bin/python -m tools.trace.cli show $ARGUMENTS

4. Report violations grouped by rule, with the shortest path to fixing each:
   - R1 — the requirement needs a spec: run `/sdd-spec <ID>`.
   - R2 — the requirement needs a test carrying its marker.
   - R3 — an ID is referenced that does not exist: fix the typo or create the note.
   - R4 — the step left no outcome note.
   - R5 — a correctness constraint advanced without a test. This is the one
     rule never to work around; write the test.
   - R6 — a dependency cycle: break it by removing the weaker `depends_on`.
5. If the dashboard changed, commit it.
```

- [ ] **Step 7: Write `CLAUDE.md`**

```markdown
# market-forge

ChannelFlow: a crypto market-structure and signal radar. The PRD
(`channel_flow_prd_codex_ua_v5.md`, 7380 lines) is the source of truth and is
**read-only** — requirements quote it, nobody edits it.

## How work happens here

Every unit of work goes through spec-driven development and leaves a trace:

    /sdd-requirement <PRD ref>   → a REQ note in vault/10-requirements/
    /sdd-spec <REQ-ID>           → Spec Kit spec + outcome note, status: specified
    /sdd-plan <REQ-ID>           → Spec Kit plan + outcome note, status: planned
    /sdd-tasks <REQ-ID>          → Spec Kit tasks + analyze + outcome note
    /sdd-implement <REQ-ID>      → tests first, then code, status: implemented
    /sdd-trace [REQ-ID]          → rebuild the graph, report gaps

Do not skip straight to code. If a change has no requirement ID, it has no
place in the graph, and `make validate` will not see it.

## The rules that are not negotiable

`.specify/memory/constitution.md` holds PRD §0 as fourteen governing
principles. The two that catch people out:

- **No look-ahead.** A feature at time `t` uses only data with
  `event_time <= t` that was actually available then. A better backtest is
  never a justification.
- **Correctness constraints need tests.** Requirements of type `constraint`
  (anti-bias rules, non-repainting tests, §0 principles) cannot advance past
  `specified` without a test. That is validator rule R5, and it is not waivable.

## Traceability

| Artifact | Carries |
|---|---|
| Requirement note | `id:` frontmatter in `vault/10-requirements/` |
| Spec | `traces: [REQ-...]` frontmatter in `specs/<NNN-slug>/spec.md` |
| Test | `@pytest.mark.trace("REQ-...")` |
| Source | `# @trace: REQ-...` comment |
| Outcome | `records: [REQ-...]` frontmatter in `vault/40-outcomes/` |

`make validate` fails the build when a requirement's status outruns its
artifacts. `make graph` rebuilds `.trace/graph.json` and regenerates the
dashboard and each note's `Trace` section — only between
`<!-- trace:begin -->` and `<!-- trace:end -->`. Everything outside those
markers is hand-written and is never machine-rewritten.

## Two vaults, one authoritative

- `vault/` — hand-written, committed, authoritative.
- `graphify-out/obsidian/` — generated by Graphify, gitignored, disposable.

Never edit the second one and never cite it as a source.

## Commands

    make install     # venv + dependencies
    make test        # pytest
    make lint        # ruff
    make graph       # rebuild graph + dashboard + Trace sections
    make validate    # coverage rules; exits 1 on violations

## Language

Artifacts (notes, specs, code, comments, commit messages) are in English.
Conversation with the user is in Ukrainian.
```

- [ ] **Step 8: Verify the commands are visible**

```bash
ls .claude/commands/
make validate
```

Expected: the six `sdd-*.md` files alongside Spec Kit's `speckit.*.md` files, and `trace: clean`.

- [ ] **Step 9: Commit**

```bash
git add .claude/commands/sdd-*.md CLAUDE.md
git commit -m "Add the SDD slash commands and project instructions

Each /sdd-* command adds exactly two things to its /speckit.* counterpart:
an outcome note and a status transition. CLAUDE.md states which of the two
Obsidian vaults is authoritative, because the generated one is easy to
mistake for the real one."
```

---

## Task 13: Graphify semantic index (optional, consent-gated)

**Files:**
- Modify: `Makefile`, `.gitignore` (already covers `graphify-out/`)

**Interfaces:**
- Consumes: nothing. Nothing consumes it. If this task is skipped, everything else still works.

- [ ] **Step 1: Ask before installing**

`graphify install` writes `~/.claude/skills/graphify/SKILL.md` and edits
`~/.claude/CLAUDE.md` — both outside this repository. Its document extraction
also calls an LLM, so indexing is neither free nor purely local.

Ask the user, in Ukrainian, whether to proceed. Show the exact commands. If they
decline, skip to Step 5 and note the decision in an ADR.

- [ ] **Step 2: Install**

```bash
uv pip install --python .venv/bin/python graphifyy
.venv/bin/graphify --version
.venv/bin/graphify install
```

- [ ] **Step 3: Build the index**

```bash
.venv/bin/graphify . --update
ls graphify-out/
```

Expected: `graph.json`, `graph.html`, `GRAPH_REPORT.md`, `obsidian/`, `cache/`.

- [ ] **Step 4: Add the Makefile target**

```makefile
.PHONY: index
index:
	$(VENV)/bin/graphify . --update
```

- [ ] **Step 5: Record the decision**

Write `vault/20-decisions/ADR-001.md`:

```markdown
---
id: ADR-001
title: Graphify provides semantic search, not traceability
status: accepted
decides: []
date: 2026-09-07
---

## Context

Graphify turns a folder into a queryable knowledge graph using tree-sitter for
code and an LLM for documents. It is good at "what connects X to Y" and bad at
"prove every requirement has a test", because its edges are fuzzy and it labels
them EXTRACTED, INFERRED or AMBIGUOUS.

## Decision

Graphify is a semantic convenience layer only. The deterministic trace graph in
`tools/trace/` is the authority for coverage, and nothing in it imports or
reads Graphify output.

`graphify-out/` is gitignored, including the Obsidian vault Graphify generates
under `graphify-out/obsidian/`. That generated vault is not `vault/`.

## Consequences

- Declining or removing Graphify costs only semantic search.
- Graphify's index may drift from the repo; it is rebuilt with `make index`,
  never trusted as a source of truth.
- An LLM call is made when indexing documents, so `make index` is run
  deliberately, not on every commit.
```

- [ ] **Step 6: Commit**

```bash
git add Makefile vault/20-decisions/ADR-001.md
git commit -m "Add optional Graphify index and record its boundary

Graphify answers 'what connects to what'; it never answers 'is this
covered'. The ADR fixes that boundary so nobody later wires the validator
to a fuzzy edge."
```

---

## Task 14: Dogfood the pipeline on REQ-INFRA-001

**Files:**
- Create: `vault/10-requirements/REQ-INFRA-001.md`, `specs/<NNN>-traceability-tooling/`, outcome notes
- Modify: `tools/trace/*.py` (add `# @trace:` markers), `tests/tools/trace/*.py` (add markers)

**Interfaces:**
- Consumes: everything built in Tasks 1–12.
- Produces: proof that the pipeline carries a real requirement end to end.

A pipeline that cannot carry its own tooling will not carry Phase 0. This task
runs the trace tool through its own process, retroactively.

- [ ] **Step 1: Write the requirement**

Create `vault/10-requirements/REQ-INFRA-001.md` from the template:

```markdown
---
id: REQ-INFRA-001
title: Deterministic traceability graph with a coverage validator
type: infrastructure
prd_ref: "§0.13, §0.14"
prd_lines: "27-28"
phase: null
status: draft
depends_on: []
tags: [tooling, traceability]
---

## Requirement

The repository holds a deterministic graph linking the PRD to requirements,
specs, tests and source, and a validator that exits non-zero when a
requirement's status outruns the artifacts that justify it.

Links are explicit and machine-checkable: `traces:` frontmatter on specs,
`@pytest.mark.trace(...)` on tests, `# @trace:` comments in source. Nothing in
the graph or the validator depends on a fuzzy or LLM-derived edge.

## Acceptance

- `make validate` exits 0 on a clean repository and 1 when any rule R1-R7 fails.
- Each of the seven rules has a passing and a failing test.
- Rule R5 is proven independent of R2: a `constraint` requirement at `planned`
  with no test fails R5 while passing R2.
- `make graph` is idempotent: running it twice leaves the working tree clean.
- Regenerating a requirement note preserves every line outside the
  `trace:begin`/`trace:end` markers.
- Test links are read from pytest's own collection, so parametrized tests are
  counted per case.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Written after the tooling existed, to prove the pipeline can carry a real
requirement. The retroactive order is deliberate and is not the pattern for
future work.
```

- [ ] **Step 2: Run the spec step**

```
/sdd-spec REQ-INFRA-001
```

The spec describes what was built in Tasks 4–10. Set `traces: [REQ-INFRA-001]`.

- [ ] **Step 3: Run the plan and tasks steps**

```
/sdd-plan REQ-INFRA-001
/sdd-tasks REQ-INFRA-001
```

- [ ] **Step 4: Add trace markers to the existing tests**

Add the marker to at least one test per module, choosing the test that most
directly demonstrates the requirement:

```python
@pytest.mark.trace("REQ-INFRA-001")
def test_r5_fails_for_a_planned_constraint_without_a_test(vault):
    ...
```

Apply the same to `test_graph.py::test_build_graph_wires_every_edge_kind`,
`test_dashboard.py::test_update_requirement_notes_is_idempotent`,
`test_cli.py::test_validate_exits_one_and_names_the_rule`, and
`test_pytest_plugin.py::test_parametrized_tests_are_recorded_once_per_case`.

- [ ] **Step 5: Add trace markers to the source**

Add `# @trace: REQ-INFRA-001` near the top of `tools/trace/model.py`,
`collect.py`, `graph.py`, `validate.py`, `dashboard.py`, `cli.py` and
`pytest_plugin.py`.

- [ ] **Step 6: Write the implement outcome and advance the status**

Create `vault/40-outcomes/OUT-2026-09-07-implement-traceability-tooling.md` with
`step: implement` and `records: [REQ-INFRA-001]`. Set the requirement's
`status: implemented`.

- [ ] **Step 7: Verify the loop closes**

```bash
make test
make graph
make validate
.venv/bin/python -m tools.trace.cli show REQ-INFRA-001
```

Expected:
- All tests pass.
- `trace: clean`.
- `show` prints the spec, five tests, seven source files and at least four
  outcome notes.

- [ ] **Step 8: Verify idempotence**

```bash
make graph
git status --short
```

Expected: no changes. If `make graph` dirties the tree on a second run, the
dashboard or the note regeneration is non-deterministic — fix it before
committing, because a dashboard that changes on every run is a dashboard nobody
will read in a diff.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "Trace the traceability tooling through its own pipeline

REQ-INFRA-001 now carries a spec, plan, tasks, five verifying tests, seven
implementing source files and four outcome notes. The pipeline has been
shown to carry a real requirement before Phase 0 depends on it."
```

---

## Definition of Done

- `.venv` on Python 3.12 with working `specify`; `.specify/` initialised with a
  constitution derived from PRD §0 and a spec template that carries `traces:`.
- `vault/` holds 87 requirement notes (86 from the PRD plus `REQ-INFRA-001`),
  four templates, an index and a generated dashboard.
- `make test` passes; the trace package has tests for every module and every
  validator rule.
- `make graph && make validate` succeeds and is idempotent.
- `REQ-INFRA-001` reads `implemented` with spec, tests, code and outcomes linked.
- `CLAUDE.md` documents the loop, and the six `/sdd-*` commands exist.
- Graphify is either installed with `make index` working, or explicitly declined
  and recorded in ADR-001.

## What this plan deliberately does not build

No ChannelFlow product code — no connectors, bars, channels, signals, storage or
UI. Phase 0 (WP-001 project bootstrap, WP-002 domain model) is the next
iteration, and it will be specified through the pipeline this plan delivers
rather than written directly.
