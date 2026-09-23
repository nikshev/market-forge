---
id: OUT-2026-09-23-spec-opencode-agent-workflow
step: spec
records: [REQ-INFRA-005]
commit: null
---

## What was done

Specified OpenCode's ChannelFlow roles, project commands, instruction and skill
loading, fallback configuration, and alignment with the existing SDD workflow.
Added a specification quality checklist and linked the spec to its requirement.

## What was decided

The existing `.claude/commands/` remains canonical; OpenCode exposes the same
six SDD workflows through project command entries. Agent roles and fallback
routing follow `/opt/parts-agent`, while their prompts and repository policies
are adapted to ChannelFlow's `REQ-*` traceability and correctness rules.

## What is still open

No specification questions remain. Technical planning and test-first
implementation are the next workflow phases.
