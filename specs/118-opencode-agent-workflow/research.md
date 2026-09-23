# Research: OpenCode Agent Workflow

**Date**: 2026-09-23

## Decisions

### 1. Source Setup Selection

**Decision**: Use `/opt/parts-agent/.opencode` as the source for agent roles, fallback model routing, plugin selection, and OpenRouter timeouts.

**Rationale**: The user explicitly requested copying from this location. Its setup includes:
- Four roles: architect (proxy), implementer (with fallback chain), implementer-senior (with fallback chain), reviewer (proxy, read-only)
- `@razroo/opencode-model-fallback` plugin for automatic model fallback
- OpenRouter timeouts (900s)
- Codex and Claude CLI fallbacks for proxy agents

**Alternatives considered**: 
- Creating roles from scratch — rejected because the request was to adapt existing working setup.
- Using `/opt/trace-forge` or `/opt/student123` — neither has `.opencode` directory.

### 2. Agent Role Mapping

**Decision**: Map parts-agent roles directly to ChannelFlow with adapted prompts:

| parts-agent | ChannelFlow | Changes |
|-------------|-------------|---------|
| architect (proxy) | architect (proxy) | Prompt rewritten for ChannelFlow REQ/constitution; Codex GPT-5.6-sol |
| implementer | implementer | Same model/fallback chain; prompt requires REQ-ID, @pytest.mark.trace, # @trace |
| implementer-senior | implementer-senior | Same model/fallback chain; prompt adds boundary/adversarial tests |
| reviewer (proxy) | reviewer (proxy) | Same Codex GPT-5.5 / Sonnet fallback; edit: deny |

**Rationale**: Preserves proven model routing while aligning every prompt with ChannelFlow's traceability and correctness rules.

**Alternatives considered**: Different model routes — rejected to keep source setup's proven fallback behavior.

### 3. Command Mapping

**Decision**: Six `/sdd-*` commands, each a thin wrapper delegating to `.claude/commands/sdd-*.md`.

**Rationale**: The repository's canonical SDD workflow lives in `.claude/commands/`; OpenCode commands must not create parallel paths or skip steps (outcome notes, status changes, trace, validation, commit).

**Alternatives considered**: Inlining full workflow in OpenCode commands — rejected to maintain single source of truth.

### 4. Configuration Schema Compliance

**Decision**: Use published OpenCode config schema (`$schema: https://opencode.ai/config.json`).

**Rationale**: OpenCode hard-fails on invalid config; schema declaration enables editor validation.

**Alternatives considered**: Omitting schema — rejected per skill guidance.

### 5. Skill Discovery

**Decision**: Add `.claude/skills` to `skills.paths` in opencode.json.

**Rationale**: The repository's Spec Kit skills live there and must be available to `/sdd-*` commands that invoke them via the skill tool.

### 6. Instruction Files

**Decision**: `instructions: ["AGENTS.md", "CLAUDE.md"]` in opencode.json.

**Rationale**: Both files are authoritative; AGENTS.md is the OpenCode/Codex entry point, CLAUDE.md has full workflow detail.

### 7. AGENTS.md Alignment

**Decision**: AGENTS.md mirrors CLAUDE.md's mandatory rules without duplication.

**Rationale**: AGENTS.md is the OpenCode-facing summary; CLAUDE.md is the detailed reference. Both must agree on PRD immutability, status ladder, R5 gate, trace markers, no-look-ahead, live/replay parity.

## No NEEDS CLARIFICATION markers remain.

All decisions are derived from the explicit user request, the source setup at `/opt/parts-agent`, and the target repository's existing workflow documented in `CLAUDE.md` and `.specify/memory/constitution.md`.