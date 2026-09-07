---
id: OUT-2026-09-07-plan-project-bootstrap
step: plan
records: [REQ-WP-001]
commit: null
---

## What was done

Planned REQ-WP-001. Produced `plan.md`, `research.md` and `quickstart.md` under
`specs/002-project-bootstrap/`. Constitution Check passed with no violations,
so Complexity Tracking is empty.

## What was decided

- **The Constitution Check names the five principles that bind this feature and
  says plainly that the other nine have no surface here.** Ticking all fourteen
  would have been theatre, and worse, it would teach the next reader that the
  check is a formality. The five that bind: VII (why MinIO, not a directory), X
  (credentials in an env file), XI (pinned images and a committed lockfile),
  XII (no performance work), XIV (this feature traces to REQ-WP-001).
- **`data-model.md` and `contracts/` are deliberately not produced**, and the
  plan says why rather than emitting placeholders. This feature introduces no
  domain entities and serves no API. A stub `data-model.md` here would be read
  as the real one when REQ-WP-002 arrives.
- **Images pinned to explicit minor tags, not `latest` and not digests.**
  `latest` breaks Principle XI outright. Digests were rejected as friction that
  buys little over a minor tag — recorded in `research.md` so the trade-off is
  visible if a patch release ever breaks the stack.
- **`infra/`, `configs/`, `migrations/` and `research/` from PRD §37 are not
  created.** They are omitted rather than made empty, because an empty directory
  in a repository is an invitation to guess what belongs in it. Each arrives
  with the feature that populates it.
- **Strict typing scoped to `src/` only.** `tools/trace/` predates the decision
  and retrofitting it is real work with no bearing on market-data correctness.
  Folding that cost into a bootstrap feature would hide it; if it is worth doing
  it deserves its own requirement.
- **PostgreSQL 16 over 17.** Nothing in PRD §30's data model needs a 17-only
  feature, and the newer major narrows the managed offerings available later.

## What is still open

- **Whether "services boot locally" in Phase 0's acceptance means backing
  services only.** This plan reads it that way and containerises no application
  service. `research.md` records the alternative reading. It resolves when
  REQ-PHASE-0 is closed, not here, and adding a service to a working compose
  file is cheap if the reading turns out wrong.
- **The MinIO image tag is not yet fixed to a specific dated release.** The
  decision to pin is made; the exact tag is chosen during implementation against
  what is current and stable then.
- **No migration tool has been selected.** Out of scope here — REQ-WP-002 brings
  the domain model and the question of how its schema reaches PostgreSQL.
- **`tools/trace/` remains outside strict typing.** Recorded as a deliberate
  gap, not an oversight. It has no requirement covering it.
