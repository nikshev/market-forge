---
description: Extract a PRD section into a new requirement note in the vault
argument-hint: <PRD section reference, e.g. "§13.2" or "WP-021">
---

Create a requirement note from the PRD section `$ARGUMENTS`.

1. Read the named section of `channel_flow_prd_codex_ua_v5.md`. **Never modify
   it** — it is read-only, always.
2. Choose an ID: `REQ-<KIND>-<TOKEN>`. Reuse an existing kind from
   `vault/10-requirements/` (currently in use: `US`, `WP`, `EXP`, `PHASE`,
   `PRIN`, `BIAS`, `NRT`; `INFRA` is reserved for infrastructure work that has
   no PRD section) unless none genuinely fits. List
   `vault/10-requirements/REQ-<KIND>-*.md` to find the next free token. IDs
   are permanent — never renumber or reuse one once it exists.
3. Copy `vault/_templates/requirement.md` to `vault/10-requirements/<ID>.md`
   and fill it:
   - `id`, `title`, `type` (one of `user-story`, `work-package`, `phase`,
     `constraint`, `experiment` — match the existing convention for the kind
     you chose), `prd_ref`, `prd_lines`, `phase` (or `null`), `depends_on`,
     `tags`.
   - The `## Requirement` section: a faithful English statement. Where the
     PRD gives a formula, threshold or state machine, reproduce it verbatim
     rather than paraphrasing it.
4. Fill `## Acceptance` with observable, checkable conditions. If the PRD
   section genuinely states none, write the note's own
   `_ACCEPTANCE-NOT-SPECIFIED: ..._` marker there (see any existing note that
   carries it for the exact wording) rather than inventing criteria the PRD
   doesn't support. A requirement in that state may not leave `draft` until a
   human replaces the marker with real acceptance criteria.
5. Set `depends_on` for any requirement this one genuinely needs first. Do
   not invent a dependency to look thorough.
6. Leave the `## Trace` section exactly as the template has it (between the
   `<!-- trace:begin -->` / `<!-- trace:end -->` markers) — `make graph`
   fills it in. Do not hand-write anything there.
7. Leave `status: draft`.
8. Run `make graph && make validate`. Both must pass before you report done.
