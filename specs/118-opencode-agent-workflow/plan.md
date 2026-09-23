# Implementation Plan: OpenCode Agent Workflow

**Branch**: `118-opencode-agent-workflow` | **Date**: 2026-09-23 | **Spec**: specs/118-opencode-agent-workflow/spec.md

**Input**: Feature specification from `/specs/118-opencode-agent-workflow/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Configure OpenCode to follow ChannelFlow's traced SDD workflow by creating a project config (`opencode.json`), four role-specific agents (`architect`, `implementer`, `implementer-senior`, `reviewer`), six `/sdd-*` command entry points, and an adapted `AGENTS.md` that aligns with `CLAUDE.md`. The setup adopts the model-fallback plugin, OpenRouter timeouts, and role routes from `/opt/parts-agent`, with all prompts and policies rewritten for ChannelFlow's `REQ-*` traceability, no-look-ahead, and live/replay-parity constraints.

## Technical Context

**Language/Version**: JSON, Markdown (configuration files)

**Primary Dependencies**: OpenCode CLI, `@razroo/opencode-model-fallback` plugin, OpenRouter provider

**Storage**: Files under `.opencode/`, `AGENTS.md`, `opencode.json`

**Testing**: Configuration validation via `opencode debug config`, `opencode agent list`, `opencode debug agent <name>`

**Target Platform**: OpenCode runtime (Linux/macOS/Windows)

**Project Type**: Developer tooling / repository configuration

**Performance Goals**: OpenCode starts without config errors; agents and commands discover correctly

**Constraints**: Must follow OpenCode config schema; must not bypass SDD workflow; reviewer must be read-only

**Scale/Scope**: 1 config file, 4 agent files, 6 command files, 1 AGENTS.md

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. No look-ahead | PASS | Configuration only; no market-data logic |
| II. Time is not one thing | PASS | N/A |
| III. History immutable | PASS | Config files are versioned |
| IV. Baselines before models | PASS | N/A |
| V. Calibration not accuracy | PASS | N/A |
| VI. Every feature documented | PASS | AGENTS.md documents the workflow |
| VII. Live/replay same code | PASS | No code divergence possible |
| VIII. Connectors share interface | PASS | N/A |
| IX. No automatic execution | PASS | N/A |
| X. Thresholds configurable | PASS | N/A |
| XI. Results reproducible | PASS | Config is versioned |
| XII. Correctness precedes performance | PASS | Validation gates enforced |
| XIII. Work incremental | PASS | SDD workflow enforced |
| XIV. Everything traceable | PASS | REQ-INFRA-005 linked throughout |

No gates violated; no complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/118-opencode-agent-workflow/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (empty — no external interfaces)
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
.opencode/
├── agents/
│   ├── architect.md
│   ├── implementer.md
│   ├── implementer-senior.md
│   └── reviewer.md
└── commands/
    ├── sdd-requirement.md
    ├── sdd-spec.md
    ├── sdd-plan.md
    ├── sdd-tasks.md
    ├── sdd-implement.md
    └── sdd-trace.md

opencode.json
AGENTS.md
```

**Structure Decision**: Configuration-only feature. Files placed at repository root and under `.opencode/` per OpenCode conventions. No `src/` or `tests/` changes needed — validation is via OpenCode CLI commands.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
