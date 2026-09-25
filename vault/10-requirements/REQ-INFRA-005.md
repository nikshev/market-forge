---
id: REQ-INFRA-005
title: OpenCode follows ChannelFlow's traced SDD workflow
type: infrastructure
prd_ref: "§0.9, §0.13, §0.14; repository practice"
prd_lines: "23, 26-28"
phase: null
status: implemented
depends_on: []
tags: [tooling, opencode, traceability]
---

## Requirement

OpenCode must use ChannelFlow's repository rules and SDD workflow rather than
the configuration of another project unchanged. Its project configuration must
expose the `architect`, `implementer`, `implementer-senior`, and read-only
`reviewer` roles, along with the repository's six `/sdd-*` commands. Model
fallback, skill discovery, and provider timeouts must be configured from the
existing `/opt/parts-agent` setup where applicable. The project `AGENTS.md` must
agree with `CLAUDE.md` on the read-only PRD, requirement traceability,
test-first workflow, and correctness constraints.

This is repository infrastructure rather than a product capability stated by
the PRD. PRD §0.9, §0.13, and §0.14 provide the governing context of testable,
incremental work with correctness before performance; Constitution XIV and
`CLAUDE.md` define the repository's traceability workflow.

## Acceptance

- The OpenCode project config is accepted by the installed CLI and uses the
  published config schema. It loads the project's `.claude/skills` and preserves
  the source setup's model-fallback plugin and OpenRouter timeouts.
- OpenCode discovers all four configured roles; the reviewer cannot edit, and
  the implementer roles expose the source setup's primary and fallback models.
- OpenCode discovers exactly the six project `/sdd-*` command entry points, and
  each delegates to the corresponding canonical workflow in
  `.claude/commands/` without exposing a shortcut around it.
- `AGENTS.md` agrees with `CLAUDE.md` on the mandatory SDD lifecycle, status
  ladder, PRD immutability, trace markers, no-look-ahead, live/replay parity,
  and hard-gated R5 requirements.
- The configuration and instructions contain no Parts Search Orchestrator
  terminology or `FR-*` trace markers.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-118-opencode-agent-workflow]]
- **Tests:**
    - `tests/unit/test_opencode_config.py::test_agents_md_has_required_rules`
    - `tests/unit/test_opencode_config.py::test_implementer_fallback_chain`
    - `tests/unit/test_opencode_config.py::test_implementer_senior_fallback_chain`
    - `tests/unit/test_opencode_config.py::test_no_foreign_terminology`
    - `tests/unit/test_opencode_config.py::test_opencode_config_validates`
    - `tests/unit/test_opencode_config.py::test_opencode_has_six_sdd_commands`
    - `tests/unit/test_opencode_config.py::test_reviewer_is_read_only`
- **Code:**
    - `tools/validate_opencode_config.py`
- **Outcomes:** [[OUT-2026-09-23-implement-opencode-agent-workflow]], [[OUT-2026-09-23-plan-opencode-agent-workflow]], [[OUT-2026-09-23-spec-opencode-agent-workflow]]
<!-- trace:end -->

## Notes

The request to adapt `/opt/parts-agent/.opencode` is the source for this
repository-infrastructure requirement. Project-specific SDD command bodies stay
canonical in `.claude/commands/`; the OpenCode commands expose those workflows.
