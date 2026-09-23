# Data Model: OpenCode Agent Workflow

**Date**: 2026-09-23

## Configuration Entities

### 1. Project Config (`opencode.json`)

Root-level OpenCode project configuration.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `$schema` | string | Yes | `https://opencode.ai/config.json` |
| `instructions` | string[] | Yes | `["AGENTS.md", "CLAUDE.md"]` |
| `skills.paths` | string[] | Yes | `[".claude/skills"]` |
| `plugin` | string[] | Yes | `["@razroo/opencode-model-fallback"]` |
| `provider.openrouter.options` | object | Yes | `{timeout, headerTimeout, chunkTimeout: 900000}` |
| `agent` | object | Yes | Four custom agents (see below) |
| `command` | object | Yes | Six SDD command entries (see below) |

### 2. Agent Configuration (`agent.<name>`)

Each agent is an object conforming to OpenCode's AgentConfig schema.

| Agent | Mode | Model | Fallback Models | Permission | Key Prompt Requirements |
|-------|------|-------|-----------------|------------|-------------------------|
| architect | all | (none — proxy) | — | default | Delegates to Codex GPT-5.6-sol; fallback to Claude Opus |
| implementer | all | opencode/mimo-v2.6-flash-free | nemotron-3.5-lightning-free, ling-3.0-flash-fin-free, muse-spark-1.3-contributor-free | default | One task, test-first, REQ trace markers, no-look-ahead |
| implementer-senior | all | opencode/nemotron-3-ultra-free | muse-spark-1.3-contributor-free, muse-spark-1.2-contributor-free, big-pickle | default | Escalated/critical tasks, boundary tests, reads prior logs |
| reviewer | all | (none — proxy) | — | `edit: deny` | Delegates to Codex GPT-5.5 read-only; fallback to Claude Sonnet |

### 3. Command Configuration (`command.<name>`)

Each command is an object with `description` and `template` fields.

| Command | Template Delegates To |
|---------|----------------------|
| sdd-requirement | `.claude/commands/sdd-requirement.md` |
| sdd-spec | `.claude/commands/sdd-spec.md` |
| sdd-plan | `.claude/commands/sdd-plan.md` |
| sdd-tasks | `.claude/commands/sdd-tasks.md` |
| sdd-implement | `.claude/commands/sdd-implement.md` |
| sdd-trace | `.claude/commands/sdd-trace.md` |

### 4. AGENTS.md

Markdown document with sections:
- Before work (git status, requirements, spec)
- Required SDD workflow (six commands, status ladder)
- Non-negotiable correctness (no-look-ahead, live/replay, R5 gate)
- OpenCode setup (agents, commands, sequential execution)
- Language (English artifacts, Ukrainian conversation)

## Validation Rules

- `opencode.json` must parse against published schema
- All four agents must be discoverable via `opencode agent list`
- All six commands must be invokable via `/sdd-*`
- `reviewer` permission must deny `edit`
- `implementer` and `implementer-senior` must have non-empty `fallback_models`
- No `FR-*` or Parts Search Orchestrator references in any file