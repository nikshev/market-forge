---
id: OUT-2026-09-11-requirement-dataset-lineage
step: requirement
records: [REQ-WP-040]
commit: null
---

## What was done

`vault/10-requirements/REQ-WP-040.md`, from PRD §0 item 13 against §23.9's field
list. [[REQ-PHASE-7]] gains a requirement after being closed, which is worth
naming rather than hiding: the phase's acceptance held on what it claimed, and
this is a hole in a *governing principle* that the phase's own list never
mentioned.

## What was decided

- **Four things are required and three are recorded.** §0 item 13 asks for a
  versioned dataset, config, code commit and artifact hash. §23.9 carries the
  last three and has no field for the first — the one the others are meaningless
  without. A registration today lets you rebuild the model and not the result.
- **The content hash goes in, not only the snapshot id.** An id is a name; a
  hash is a claim about what was under it. [[ADR-053]] made that distinction for
  datasets and it is the same distinction here.
- **Refused rather than defaulted**, per [[ADR-015]]: a field with a default is
  a field an author can forget to think about, and this one selects whether a
  result is checkable at all.
- **[[ADR-058]] is the precedent.** §23.9's list already grew a twelfth field
  when §41 rule 10 demanded something it did not carry. The list describes the
  artifact; §0 governs.

## What this closes

[[REQ-WP-038]]'s retention keeps snapshots a lineage names and has no lineage to
read, so today a caller pins by hand or prunes without pins. That gap was
recorded when it was found rather than designed around, and this is the work it
was waiting for.

## What is still open

- **Whether a study cites one dataset or one per fold.** A run reads one table
  at one snapshot, so one is right today; a walk-forward study over several
  tables would need more, and nothing does that yet.
