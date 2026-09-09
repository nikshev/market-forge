# market-forge Knowledge Vault

This vault is the record of how ChannelFlow gets built. It is committed to git,
so every note carries the same history as the code it describes.

## Layout

| Folder | Holds |
|---|---|
| `10-requirements/` | One note per requirement, extracted from the PRD. IDs are permanent. |
| `20-decisions/` | ADRs. Decisions that were not obvious and cost something. |
| `30-specs/` | One note per Spec Kit spec, so specs appear in the graph. |
| `40-outcomes/` | One note per SDD step. What happened, what was decided, what is open. |
| `50-experiments/` | PRD §39 research experiments and their results. |
| `_templates/` | Note templates. |

## Rules

- The PRD (`channel_flow_prd_codex_ua_v5.md`) is read-only. Requirements quote
  it; nobody edits it.
- Requirement IDs are permanent. Retire a requirement by setting its status,
  never by renumbering or deleting it.
- `Trace` sections are generated between `trace:begin`/`trace:end` markers.
  Everything else in a note is hand-written and is never machine-rewritten.
- Constraint notes derived from PRD §0 (`REQ-PRIN-*`) and §41 (`REQ-BIAS-*`)
  carry their rule text as their `## Acceptance` verbatim, by design: for a
  flat prohibition ("no random train/test primary split"), the prohibition
  *is* the checkable condition, so there is nothing further to extract. This
  is distinct from the 10 notes that genuinely lacked acceptance criteria and
  carried the `ACCEPTANCE-NOT-SPECIFIED` marker. All ten now carry derived
  criteria instead, each line naming the PRD section it comes from; the three
  derivations live under `docs/superpowers/specs/`.
- `graphify-out/obsidian/` is a *different*, generated, gitignored vault. This
  one is authoritative.

## Entry points

- [[Traceability Dashboard]]
