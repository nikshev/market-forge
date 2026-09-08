---
id: REQ-WP-001
title: Project bootstrap
type: work-package
prd_ref: "WP-001 Project bootstrap"
prd_lines: "6920-6936"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

Tasks:

- create pyproject;
- setup `uv`;
- ruff;
- mypy/pyright optional;
- pytest;
- frontend scaffold;
- docker compose;
- Makefile.

Done when:

- one command starts dev stack.

## Acceptance

- one command starts dev stack.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-002-project-bootstrap]]
- **Tests:**
    - `tests/integration/test_dev_stack.py::test_object_store_lists_buckets`
    - `tests/integration/test_dev_stack.py::test_postgres_answers_a_query`
- **Code:**
    - `apps/web/src/App.tsx`
    - `src/channelflow/__init__.py`
- **Outcomes:** [[OUT-2026-09-07-implement-project-bootstrap]], [[OUT-2026-09-07-plan-project-bootstrap]], [[OUT-2026-09-07-spec-project-bootstrap]], [[OUT-2026-09-07-tasks-project-bootstrap]], [[OUT-2026-09-08-implement-trace-apps-root]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
