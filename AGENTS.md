# market-forge — agent operating rules

ChannelFlow is a crypto market-structure and signal radar. `CLAUDE.md` contains
the detailed repository workflow and traceability rules; read it before making
changes. `.specify/memory/constitution.md` is governing policy, and the PRD
`channel_flow_prd_codex_ua_v5.md` is the read-only product source of truth.

## Before work

1. Check `git status`, `git diff`, and recent commits. Preserve existing user
   changes; do not overwrite work already in progress.
2. Read the relevant requirement note in `vault/10-requirements/`, its active
   `specs/<NNN-slug>/spec.md`, and related plan/tasks before implementation.
3. Do not implement work that has no real requirement ID and accepted
   specification. Extract requirements from the PRD with `/sdd-requirement`;
   never edit the PRD.

## Required SDD workflow

Use the repository's `/sdd-*` commands in order:

```text
/sdd-requirement <PRD reference>
/sdd-spec <REQ-ID>
/sdd-plan <REQ-ID>
/sdd-tasks <REQ-ID>
/sdd-implement <REQ-ID>
/sdd-trace [REQ-ID]
```

Each workflow records an outcome note and updates the requirement status as
specified by its command. The status ladder is `draft → specified → planned →
tested → implemented → verified`. `tested` is evidence that tests were written
first; because the repository's full validation requires a passing suite, the
RED evidence is recorded in the outcome note and the `tested` status is
committed with the implementation. Do not skip the test-first step or claim
that a red suite was committed.

Every test verifying a requirement must carry
`@pytest.mark.trace("REQ-...")`. Every implementation source file must carry
`# @trace: REQ-...` (or `// @trace: REQ-...` in TypeScript/JavaScript). Run
`make graph && make validate` at the workflow's required checkpoints. Do not
bypass a failing trace rule or pre-commit check.

## Non-negotiable correctness

- **No look-ahead.** A value computed at time `t` may use only data with
  `event_time <= t` that was actually available at the decision moment.
- **Live and replay use the same code.** Divergence is a defect.
- **Hard-gated requirements need tests before advancing.** For
  `hard_gated: true`, R5 forbids status beyond `specified` without a linked,
  passing test. Never work around this gate.
- Keep the PRD read-only, preserve immutable history, and prefer correctness,
  replay parity, and data integrity over performance optimization. Read the
  constitution and `CLAUDE.md` for the full set of principles and validator
  rules.

## OpenCode setup

Project agents live in `.opencode/agents/`; slash commands live in
`.opencode/commands/`. The six `/sdd-*` commands mirror the repository workflow.
Use the configured roles for their intended phase:

| Work | OpenCode role |
|---|---|
| Planning and task decomposition | `architect` |
| One routine task at a time | `implementer` |
| Critical, multi-file, or escalated task | `implementer-senior` |
| Read-only review after implementation | `reviewer` |

Agents that modify files must run sequentially. Run `reviewer` after the
implementer. The implementer must complete exactly one task per run and follow
the test-first flow in `/sdd-implement`.

### OpenCode role models & fallback chains

The `@razroo/opencode-model-fallback` plugin is registered in `opencode.json`.
Agent `model` in `.opencode/agents/*.md` is the primary model; ordered
`fallback_models` is the plugin's automatic chain. The plugin switches on
provider errors (rate limit, quota, unavailable, HTTP 429/5xx). After
exhaustion the error returns; do not switch to undeclared or paid models
without explicit approval.

| Role | Primary model | Fallback chain |
|---|---|---|
| `architect` | `codex/gpt-5.6-sol` | `opencode/gpt-5.5` → `opencode/zen-claude-opus-5-5` → `claude/opus` → `claude/sonnet` |
| `implementer` | `opencode/mimo-v2.6-flash-free` | `openrouter/nvidia/nemotron-3.5-lightning:free` → `opencode/nemotron-3.5-lightning-free` → `inclusionai/ling-3.0-flash-fin:free` → `opencode/ling-3.0-flash-fin-free` |
| `implementer-senior` | `opencode/nemotron-3-ultra-free` | `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` → `opencode/muse-spark-1.3-contributor-free` → `opencode/muse-spark-1.2-contributor-free` → `openrouter/qwen/qwen3.8-27b:free` → `opencode/big-pickle` |
| `reviewer` | `codex/gpt-5.5` (read-only) | `opencode/zen-claude-sonnet-5` → `opencode/zen-claude-opus-5-5` → `claude/sonnet` → `claude/opus` |

Global `fallback_models` in `opencode.json` provides the default chain for
agents without their own `fallback_models`. `architect` and `reviewer` have
explicit `fallback_models` in their frontmatter; `implementer` and
`implementer-senior` inherit from their agent config.

After changes to `opencode.json`, `.opencode/agents/`, or the plugin, restart
OpenCode to reload settings.

For the available `make` targets, fast/full test gates, CI rules, and complete
traceability details, follow `CLAUDE.md`.

## Language

Repository artifacts, code, comments, and commit messages are in English.
Conversation with the user is in Ukrainian.
# @trace: REQ-INFRA-005
