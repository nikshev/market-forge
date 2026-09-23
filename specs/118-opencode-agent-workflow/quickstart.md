# Quickstart: OpenCode Agent Workflow Validation

**Date**: 2026-09-23

## Prerequisites

- OpenCode CLI installed (`opencode --version` shows 1.18.32 or later)
- Repository at `/opt/market-forge` with the new configuration files in place
- OpenRouter credentials configured (for provider timeouts to be relevant)
- Codex and/or Claude CLI available in PATH (for proxy agent fallbacks)

## Validation Scenarios

### 1. Config Schema Validation

**Setup**:
```bash
cd /opt/market-forge
```

**Run**:
```bash
opencode debug config
```

**Expected**:
- Exit code 0
- JSON output includes `agent` with four custom roles
- JSON output includes `command` with six `sdd-*` entries
- JSON output includes `plugin` with `@razroo/opencode-model-fallback`
- JSON output includes `skills.paths` with `.claude/skills`
- No schema validation errors

### 2. Agent Discovery

**Run**:
```bash
opencode agent list
```

**Expected**:
- Lists built-in agents plus four custom: `architect`, `implementer`, `implementer-senior`, `reviewer`
- Custom agents show `mode: all`

**Run for each agent**:
```bash
opencode debug agent architect
opencode debug agent implementer
opencode debug agent implementer-senior
opencode debug agent reviewer
```

**Expected**:
- `architect`: no `model` field, has `fallback_models` absent, prompt references ChannelFlow/REQ/constitution
- `implementer`: `model: opencode/mimo-v2.6-flash-free`, four fallback models, prompt requires REQ-ID and trace markers
- `implementer-senior`: `model: opencode/nemotron-3-ultra-free`, four fallback models, prompt reads escalation logs
- `reviewer`: `permission.edit: deny`, no `model`, prompt delegates to Codex GPT-5.5 read-only

### 3. Command Discovery

**Run**:
```bash
opencode --help | grep sdd
```

**Expected**:
- Six `sdd-*` commands listed with descriptions matching spec.md FR-004

### 4. Instruction and Skill Loading

**Run**:
```bash
opencode debug config | jq '.instructions, .skills'
```

**Expected**:
- `instructions`: `["AGENTS.md", "CLAUDE.md"]`
- `skills.paths`: `[".claude/skills"]`

### 5. SDD Workflow Smoke Test (read-only)

**Run**:
```bash
# Dry-run: show command template without executing
opencode run --agent architect "/sdd-requirement --help" 2>&1 | head -20
```

**Expected**:
- Command template references `.claude/commands/sdd-requirement.md`
- Does not execute the workflow (no argument provided)

### 6. AGENTS.md / CLAUDE.md Consistency

**Run**:
```bash
# Check both files contain the same key rules
grep -c "no-look-ahead" AGENTS.md CLAUDE.md
grep -c "live.*replay" AGENTS.md CLAUDE.md
grep -c "hard_gated" AGENTS.md CLAUDE.md
grep -c "@pytest.mark.trace" AGENTS.md CLAUDE.md
grep -c "@trace:" AGENTS.md CLAUDE.md
```

**Expected**:
- Both files mention all key rules (counts may differ but concepts present)

### 7. No Foreign Terminology

**Run**:
```bash
grep -r "parts-agent\|Parts Search\|FR-[0-9]" .opencode/ AGENTS.md opencode.json 2>/dev/null || echo "CLEAN"
```

**Expected**:
- Output: `CLEAN` (no matches)

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `opencode debug config` fails | Invalid JSON or schema violation | Fix `opencode.json`; validate with `python3 -m json.tool opencode.json` |
| Agent not listed | File not in `.opencode/agents/` or invalid frontmatter | Check file exists and frontmatter has `name`, `mode` |
| Command not found | File not in `.opencode/commands/` or missing frontmatter | Check file exists and has `description`, `template` |
| Reviewer can edit | Permission not set | Ensure `reviewer.md` frontmatter has `permission: {edit: deny}` |
| Fallback not working | Plugin not loaded | Check `@razroo/opencode-model-fallback` in `plugin` array and installed |

## Success Criteria Met When

All seven validation scenarios pass with expected outputs.