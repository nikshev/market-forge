---
description: "Task list template for feature implementation"
---

# Tasks: OpenCode Agent Workflow

**Input**: Design documents from `/specs/118-opencode-agent-workflow/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: This feature is configuration-only; validation is via OpenCode CLI commands per quickstart.md. No pytest tests are needed.

**Organization**: Tasks are grouped by user story to enable independent verification of each story's acceptance criteria.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify repository structure and tooling

- [ ] T001 Verify OpenCode CLI installed and version >= 1.18.32
- [ ] T002 Verify `@razroo/opencode-model-fallback` plugin available (npm registry)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core configuration files that all user stories depend on

- [ ] T003 Create project config `opencode.json` with schema, instructions, skills, plugin, provider
- [ ] T004 Create `AGENTS.md` aligned with `CLAUDE.md` (SDD workflow, status ladder, trace markers, correctness rules)

**Checkpoint**: Foundation ready — agent and command files can now be created

---

## Phase 3: User Story 1 - Run ChannelFlow SDD commands in OpenCode (Priority: P1) 🎯 MVP

**Goal**: OpenCode discovers and can invoke all six `/sdd-*` commands, each delegating to its canonical `.claude/commands/sdd-*.md` workflow.

**Independent Test**: `opencode --help` lists all six commands; each command's template references the matching `.claude/commands/` file.

### Implementation for User Story 1

- [ ] T005 [P] [US1] Create `.opencode/commands/sdd-requirement.md` delegating to `.claude/commands/sdd-requirement.md`
- [ ] T006 [P] [US1] Create `.opencode/commands/sdd-spec.md` delegating to `.claude/commands/sdd-spec.md`
- [ ] T007 [P] [US1] Create `.opencode/commands/sdd-plan.md` delegating to `.claude/commands/sdd-plan.md`
- [ ] T008 [P] [US1] Create `.opencode/commands/sdd-tasks.md` delegating to `.claude/commands/sdd-tasks.md`
- [ ] T009 [P] [US1] Create `.opencode/commands/sdd-implement.md` delegating to `.claude/commands/sdd-implement.md`
- [ ] T010 [P] [US1] Create `.opencode/commands/sdd-trace.md` delegating to `.claude/commands/sdd-trace.md`

**Validation per quickstart.md Scenario 3**:
- [ ] T011 [US1] Run `opencode --help | grep sdd` and verify six commands listed

### FR-006 Per-Rule Verification (US1 extension)

**Goal**: Verify AGENTS.md contains each mandatory rule from FR-006.

- [ ] T011a [US1] Verify AGENTS.md states requirement-first workflow with six `/sdd-*` commands
- [ ] T011b [US1] Verify AGENTS.md states status ladder: `draft → specified → planned → tested → implemented → verified`
- [ ] T011c [US1] Verify AGENTS.md states R5 gate: `hard_gated: true` forbids status past `specified` without test
- [ ] T011d [US1] Verify AGENTS.md states required trace markers: `@pytest.mark.trace("REQ-...")` and `# @trace: REQ-...`
- [ ] T011e [US1] Verify AGENTS.md states PRD is read-only
- [ ] T011f [US1] Verify AGENTS.md states no-look-ahead constraint
- [ ] T011g [US1] Verify AGENTS.md states live/replay parity constraint

---

## Phase 4: User Story 2 - Delegate work to purpose-specific agents (Priority: P2)

**Goal**: OpenCode discovers four custom agents with correct models, fallbacks, permissions, and ChannelFlow-aligned prompts.

**Independent Test**: `opencode agent list` shows four custom agents; `opencode debug agent <name>` shows correct model/fallback/permission for each.

### Implementation for User Story 2

- [ ] T012 [P] [US2] Create `.opencode/agents/architect.md` (proxy, no model, Codex GPT-5.6-sol, Opus fallback)
- [ ] T013 [P] [US2] Create `.opencode/agents/implementer.md` (mimo-v2.6-flash-free + 3 fallbacks, REQ-ID trace markers)
- [ ] T014 [P] [US2] Create `.opencode/agents/implementer-senior.md` (nemotron-3-ultra-free + 3 fallbacks, escalation handling)
- [ ] T015 [P] [US2] Create `.opencode/agents/reviewer.md` (permission edit: deny, proxy to Codex GPT-5.5, Sonnet fallback)

**Validation per quickstart.md Scenario 2**:
- [ ] T016 [US2] Run `opencode agent list` and verify four custom agents present
- [ ] T017 [US2] Run `opencode debug agent reviewer` and verify `edit: deny`
- [ ] T018 [US2] Run `opencode debug agent implementer` and verify fallback chain
- [ ] T019 [US2] Run `opencode debug agent implementer-senior` and verify fallback chain

---

## Phase 5: User Story 3 - Load repository rules and skills (Priority: P3)

**Goal**: OpenCode loads `AGENTS.md`, `CLAUDE.md`, and `.claude/skills`; no foreign terminology remains.

**Independent Test**: `opencode debug config` shows instructions and skills paths; grep confirms no Parts Search Orchestrator or `FR-*` references.

### Implementation for User Story 3

- [ ] T020 [P] [US3] Verify `opencode.json` includes `instructions: ["AGENTS.md", "CLAUDE.md"]`
- [ ] T021 [P] [US3] Verify `opencode.json` includes `skills.paths: [".claude/skills"]`
- [ ] T022 [P] [US3] Verify all created files use `REQ-*` trace IDs, not `FR-*`

**Validation per quickstart.md Scenarios 4, 7**:
- [ ] T023 [US3] Run `opencode debug config | jq '.instructions, .skills'` and verify

### FR-007 Full Config Verification (US3 extension)

**Goal**: Verify each config section required by FR-007 resolves correctly.

- [ ] T023a [US3] Verify `opencode.json` includes `plugin: ["@razroo/opencode-model-fallback"]`
- [ ] T023b [US3] Verify `opencode.json` includes `provider.openrouter.options` with 900000ms timeouts
- [ ] T023c [US3] Verify `opencode debug agent list` shows all four custom agents
- [ ] T023d [US3] Verify `opencode debug agent architect` shows no model (proxy)
- [ ] T023e [US3] Verify `opencode debug agent implementer` shows mimo-v2.6-flash-free + 3 fallbacks
- [ ] T023f [US3] Verify `opencode debug agent implementer-senior` shows nemotron-3-ultra-free + 3 fallbacks
- [ ] T023g [US3] Verify `opencode debug agent reviewer` shows `edit: deny`
- [ ] T023h [US3] Verify `opencode debug config | jq '.skills.paths'` includes `.claude/skills`
- [ ] T023i [US3] Verify `opencode --help | grep sdd` shows all six commands

- [ ] T024 [US3] Run `grep -r "parts-agent\|Parts Search\|FR-[0-9]" .opencode/ AGENTS.md opencode.json` and confirm CLEAN

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and cleanup

- [ ] T029 Run full quickstart.md validation suite (Scenarios 1-7)
- [ ] T030 Run `make graph && make validate` to confirm trace graph clean
- [ ] T031 Update requirement status to `implemented` in `REQ-INFRA-005.md`
- [ ] T032 Create implementation outcome note in `vault/40-outcomes/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phases 3-5)**: All depend on Foundational; can proceed in parallel
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no cross-story deps
- **US2 (P2)**: After Foundational — no cross-story deps
- **US3 (P3)**: After Foundational — no cross-story deps

### Within Each User Story

- All command/agent files are independent → marked [P]
- Validation tasks run after corresponding implementation

### Parallel Opportunities

- All Phase 1 tasks [P]
- All Phase 2 tasks [P] (different files)
- All US1 command files (T005-T010) [P]
- All US1 FR-006 verification tasks (T011a-T011g) [P]
- All US2 agent files (T012-T015) [P]
- All US3 config verification tasks (T020-T022, T023a-T023i) [P]

---

## Parallel Example: User Story 1

```bash
# All six command files can be created in parallel:
Task: "Create .opencode/commands/sdd-requirement.md"
Task: "Create .opencode/commands/sdd-spec.md"
Task: "Create .opencode/commands/sdd-plan.md"
Task: "Create .opencode/commands/sdd-tasks.md"
Task: "Create .opencode/commands/sdd-implement.md"
Task: "Create .opencode/commands/sdd-trace.md"
```

---

## Parallel Example: User Story 2

```bash
# All four agent files can be created in parallel:
Task: "Create .opencode/agents/architect.md"
Task: "Create .opencode/agents/implementer.md"
Task: "Create .opencode/agents/implementer-senior.md"
Task: "Create .opencode/agents/reviewer.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (opencode.json + AGENTS.md)
3. Complete Phase 3: User Story 1 (six command files + FR-006 rule verification)
4. **STOP and VALIDATE**: Run quickstart Scenario 1 & 3; verify AGENTS.md rules
5. If clean, proceed to US2

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (commands + AGENTS.md rule checks) → Validate → MVP: SDD commands work, rules documented
3. Add US2 (agents) → Validate → Role delegation works
4. Add US3 (skills/rules + full config verification) → Validate → Full alignment
5. Each story adds value without breaking previous stories

---

## Notes

- All tasks target `.opencode/`, root config, or `AGENTS.md` — no `src/` or `tests/` changes
- Validation is via OpenCode CLI, not pytest
- `[P]` = different files, no dependencies
- `[US#]` maps task to user story for traceability to spec.md FR-001 through FR-008
- Commit after each phase or logical group