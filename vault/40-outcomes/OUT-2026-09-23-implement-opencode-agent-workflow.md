---
id: OUT-2026-09-23-implement-opencode-agent-workflow
step: implement
records: [REQ-INFRA-005]
commit: null
---

## What was done

Implemented the complete OpenCode configuration for ChannelFlow:

1. **Project config** (`opencode.json`): Schema reference, instructions (AGENTS.md + CLAUDE.md), skills path (.claude/skills), @razroo/opencode-model-fallback plugin, OpenRouter 900s timeouts.

2. **Four custom agents** (`.opencode/agents/`):
   - `architect` — proxy to Codex GPT-5.6-sol (Opus fallback), no model field
   - `implementer` — mimo-v2.6-flash-free + 3 fallbacks, requires REQ-ID, trace markers, test-first
   - `implementer-senior` — nemotron-3-ultra-free + 3 fallbacks, escalation handling, boundary tests
   - `reviewer` — proxy to Codex GPT-5.5 read-only (Sonnet fallback), `edit: deny`

3. **Six SDD commands** (`.opencode/commands/`): `/sdd-requirement`, `/sdd-spec`, `/sdd-plan`, `/sdd-tasks`, `/sdd-implement`, `/sdd-trace` — each a thin wrapper delegating to canonical `.claude/commands/sdd-*.md`.

4. **AGENTS.md**: Aligned with CLAUDE.md — requirement-first workflow, status ladder, R5 gate, trace markers (@pytest.mark.trace, # @trace:), no-look-ahead, live/replay parity, read-only PRD.

## What was decided

- Directly adapted `/opt/parts-agent` agent roles, fallback chains, plugin, and timeouts.
- Commands are thin wrappers — canonical workflow remains in `.claude/commands/`.
- No Parts Search Orchestrator terminology or `FR-*` trace IDs in any generated file.
- Validation via OpenCode CLI (`opencode debug config`, `opencode agent list`, `opencode debug agent <name>`), not pytest.

## What is still open

None — all acceptance criteria from spec.md verified:
- SC-001: Config resolves without schema errors ✓
- SC-002: Four custom agents + six commands discovered ✓
- SC-003: Model routes match source; reviewer edit denied ✓
- SC-004: All six commands reference canonical workflow ✓
- SC-005: Trace graph clean; no foreign terminology ✓

Trace graph rebuilt and `make validate` passes (3575 nodes, 4241 edges).