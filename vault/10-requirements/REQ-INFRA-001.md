---
id: REQ-INFRA-001
title: Deterministic traceability graph with a coverage validator
type: infrastructure
prd_ref: "§0.13, §0.14"
prd_lines: "27-28"
phase: null
status: implemented
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
  generated-block markers.
- Test links are read from pytest's own collection, so parametrized tests are
  counted per case.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-001-traceability-tooling]]
- **Tests:**
    - `tests/tools/trace/test_cli.py::test_validate_exits_one_and_names_the_rule`
    - `tests/tools/trace/test_dashboard.py::test_update_requirement_notes_is_idempotent`
    - `tests/tools/trace/test_graph.py::test_build_graph_wires_every_edge_kind`
    - `tests/tools/trace/test_pytest_plugin.py::test_parametrized_tests_are_recorded_once_per_case`
    - `tests/tools/trace/test_validate.py::test_r5_fails_for_a_planned_constraint_without_a_test`
- **Code:**
    - `tools/trace/cli.py`
    - `tools/trace/collect.py`
    - `tools/trace/dashboard.py`
    - `tools/trace/graph.py`
    - `tools/trace/model.py`
    - `tools/trace/pytest_plugin.py`
    - `tools/trace/validate.py`
- **Outcomes:** [[OUT-2026-09-07-implement-traceability-tooling]], [[OUT-2026-09-07-plan-traceability-tooling]], [[OUT-2026-09-07-spec-traceability-tooling]], [[OUT-2026-09-07-tasks-traceability-tooling]]
<!-- trace:end -->

## Notes

Written after the tooling existed, to prove the pipeline can carry a real
requirement. The retroactive order is deliberate and is not the pattern for
future work.
