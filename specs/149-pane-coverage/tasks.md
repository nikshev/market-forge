---
description: "Tasks for REQ-WP-097 -- every lower pane the deployment can fill has data, and the rest say why"
---

# Tasks: Every lower pane the deployment can fill has data, and the rest say why

**Input**: `spec.md`, `plan.md`. Acceptance of specs 145-148.

## Phase 1: Tests (RED first)

- [ ] T001 [P] `tests/tools/panes/test_classify.py`: three states from API answers; reasons taken from the answers; `NO PRODUCER` exits 1; API down exits 2; a market not in the markets list is never invented
- [ ] T002 [P] `tests/mutations/panes_classify.toml`

## Phase 2: Implementation

- [ ] T003 `tools/panes/{__init__,classify,fetch,__main__}.py`, `make panes-report`

## Phase 3: Gate and live evidence

- [ ] T004 `make lint`, `make typecheck`, `make graph`; `status: tested`; commit
- [ ] T005 After specs 145-148 are deployed and have run: the recorded run, service listing with health and ages, image revision, screenshots (light/dark) in `docs/ui/`; `status: implemented`

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001-004 script, classification, exit codes | T001, T003 |
| FR-005 recorded evidence | T005 |
| SC-001-004 | T005 |
