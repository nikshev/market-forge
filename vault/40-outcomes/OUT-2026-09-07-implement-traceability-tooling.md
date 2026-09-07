---
id: OUT-2026-09-07-implement-traceability-tooling
step: implement
records: [REQ-INFRA-001]
commit: null
---

## What was done

Marked five pre-existing tests with `@pytest.mark.trace("REQ-INFRA-001")` —
one each in `tests/tools/trace/test_validate.py`
(`test_r5_fails_for_a_planned_constraint_without_a_test`),
`test_graph.py` (`test_build_graph_wires_every_edge_kind`), `test_dashboard.py`
(`test_update_requirement_notes_is_idempotent`), `test_cli.py`
(`test_validate_exits_one_and_names_the_rule`), and `test_pytest_plugin.py`
(`test_parametrized_tests_are_recorded_once_per_case`) — and added
`# @trace: REQ-INFRA-001` near the top of all seven `tools/trace/*.py`
modules (`model.py`, `collect.py`, `graph.py`, `validate.py`, `dashboard.py`,
`cli.py`, `pytest_plugin.py`). Ran the full suite (`make test`, 125 tests) to
confirm nothing broke, then `make graph && make validate`.

## What was decided

- The five tests marked were pre-existing and already passing — they encode
  behavior implemented in Tasks 4-10, not behavior written for this
  exercise. There was no "watch it fail first" step for them, unlike a
  genuinely new requirement; `specs/001-traceability-tooling/tasks.md` T013
  says this explicitly so the deviation from the usual test-first flow isn't
  silently smoothed over.
- One test file per source module, one marker per test, chosen for whichever
  existing test most directly demonstrates a distinct facet of the
  requirement (R5/R2 independence, every edge kind wired, idempotent
  regeneration, the CLI's exit-code contract, per-case parametrized
  counting) rather than marking every test that happens to touch the module.
- `tools/trace/collect.py` itself is one of the seven source files carrying
  the marker, and it is also the collector whose own regex
  (`@trace:\s*(REQ-[A-Z]+-[0-9A-Z]+)`) finds that very marker when
  `make graph` scans `tools/` — a small, deliberate bit of the tool
  verifying itself.

## What is still open

- `commit:` is left `null` in this note. The `/sdd-implement` command
  document assumes a commit per step (`tested`, then `implemented`) and says
  to fill the hash in afterward; this exercise's brief collapses everything
  into one commit at the end, so there is no natural point to backfill this
  field without a second commit. See the Task 14 report's notes on the
  `/sdd-*` command documents for detail.
- No further work is open against REQ-INFRA-001 itself; `status: verified`
  is deliberately not set here — that is a human judgement, per
  `/sdd-implement`'s closing instruction, not something this outcome note
  decides.
