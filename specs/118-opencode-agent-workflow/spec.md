---
traces: [REQ-INFRA-005]
status: draft
---

# Feature Specification: OpenCode Agent Workflow

**Feature Branch**: `[118-opencode-agent-workflow]`

**Created**: 2026-09-23

**Status**: Draft

**Input**: User description: "Copy OpenCode settings from `/opt/parts-agent/.opencode` and adapt `AGENTS.md` for ChannelFlow."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run ChannelFlow SDD commands in OpenCode (Priority: P1)

As a developer working in ChannelFlow, I can invoke the repository's six SDD
commands from OpenCode and receive the same requirement-first workflow used by
the other repository agents.

**Why this priority**: A command that is missing or bypasses the required
workflow can break requirement status and traceability.

**Independent Test**: Start OpenCode in the repository, inspect its resolved
configuration, and confirm the six `/sdd-*` command names and their canonical
workflow references are available.

**Acceptance Scenarios**:

1. **Given** the project is opened in OpenCode, **When** its commands are
   listed, **Then** `/sdd-requirement`, `/sdd-spec`, `/sdd-plan`, `/sdd-tasks`,
   `/sdd-implement`, and `/sdd-trace` are available.
2. **Given** a user invokes one of those commands, **When** the command runs,
   **Then** it follows the matching procedure in `.claude/commands/` without
   skipping its outcome, status, trace, or validation steps.

---

### User Story 2 - Delegate work to purpose-specific agents (Priority: P2)

As a developer, I can select an architect, implementer, senior implementer, or
reviewer and have each role follow ChannelFlow's requirements and correctness
rules.

**Why this priority**: Role-specific routing preserves phase boundaries and
keeps review read-only while using the model routes already adopted by the
source OpenCode setup.

**Independent Test**: Inspect the resolved agent configuration and verify the
four role names, model routes, fallback lists, and reviewer edit denial.

**Acceptance Scenarios**:

1. **Given** an OpenCode session in this repository, **When** custom agents are
   listed, **Then** the four ChannelFlow roles are discoverable.
2. **Given** the reviewer role is selected, **When** it attempts an edit,
   **Then** OpenCode denies the edit.
3. **Given** an implementation task is assigned, **When** either implementer
   role runs, **Then** it requires a real REQ ID, writes a verifying test first,
   and handles one task at a time.

---

### User Story 3 - Load repository rules and skills (Priority: P3)

As a developer, I can rely on OpenCode to load ChannelFlow-specific guidance
and Spec Kit skills rather than applying another project's terminology or
workflow.

**Why this priority**: The project policy and installed skills are the source
of truth for the repository's SDD lifecycle.

**Independent Test**: Inspect the resolved project configuration and compare
`AGENTS.md` with `CLAUDE.md` for their mandatory repository rules.

**Acceptance Scenarios**:

1. **Given** OpenCode starts in the project, **When** instructions and skills
   are loaded, **Then** it includes `AGENTS.md`, `CLAUDE.md`, and the project's
   `.claude/skills` directory.
2. **Given** an agent reads the project guidance, **When** it handles
   market-data work, **Then** it preserves the no-look-ahead and live/replay
   parity requirements and treats the PRD as read-only.

## Edge Cases

- If the project configuration is malformed, OpenCode must reject it during
  startup rather than silently running with missing role or command settings.
- If a configured fallback model or external CLI is unavailable, the agent
  must report the failure instead of switching to an undeclared model or
  bypassing the role's workflow.
- If a project skill cannot be loaded, the command must not claim that its SDD
  phase completed.
- A clean project config must coexist with the user's global OpenCode settings.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST expose `architect`, `implementer`,
  `implementer-senior`, and `reviewer` roles with their documented purposes.
- **FR-002**: The implementer roles MUST use the primary and fallback model
  routes adopted from `/opt/parts-agent`, with no undeclared paid-model fallback.
- **FR-003**: The reviewer MUST be read-only and MUST return its delegated review
  verdict without modifying project files.
- **FR-004**: The project MUST expose the six `/sdd-*` commands and each MUST
  delegate to its matching canonical `.claude/commands/sdd-*.md` workflow.
- **FR-005**: OpenCode MUST load project instructions from `AGENTS.md` and
  `CLAUDE.md`, and discover the existing project Spec Kit skills.
- **FR-006**: `AGENTS.md` MUST state the requirement-first workflow, the status
  ladder and R5 gate, the required trace markers, the read-only PRD rule, and
  the no-look-ahead and live/replay-parity constraints.
- **FR-007**: OpenCode MUST accept the project config and resolve the configured
  plugin, OpenRouter timeouts, agents, commands, and project skill path.
- **FR-008**: The copied project agent/configuration artifacts MUST NOT retain
  Parts Search Orchestrator terminology or `FR-*` trace IDs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The installed OpenCode CLI resolves the project config with exit
  status 0 and no configuration-schema errors.
- **SC-002**: The resolved project config exposes all four custom agent roles
  and all six project SDD commands.
- **SC-003**: The resolved implementer model routes match the configured source
  setup, and the resolved reviewer permission denies edits.
- **SC-004**: All six command files reference the corresponding canonical SDD
  workflow, and no command creates a direct route around that workflow.
- **SC-005**: Automated repository checks pass for the new requirement links,
  with no Parts Search Orchestrator name or `FR-*` marker in the added agent
  configuration.

## Assumptions

- The user's `/opt/parts-agent` setup is the source for OpenCode agent roles,
  fallback-model routing, plugin selection, and OpenRouter timeouts.
- The existing `.claude/commands/` and `.claude/skills/` remain the canonical
  source for ChannelFlow's SDD procedure and skills.
- OpenCode, provider credentials, and the Codex/Claude CLI routes used by proxy
  agents are installed or configured by the developer's environment.
