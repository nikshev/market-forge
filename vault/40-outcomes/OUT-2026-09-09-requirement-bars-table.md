---
id: OUT-2026-09-09-requirement-bars-table
step: requirement
records: [REQ-TBL-001]
commit: null
---

## What was done

`REQ-TBL-001`, hand-written from PRD §29.4, §29.B and §29.0.

## What was decided

- **`bars` first.** It is the table PRD §29.4 specifies most concretely, its
  producer already has a hook at exactly the right moment, and the API's most
  used read is over it.
- **The scope is one table.** The other sixteen arrive with their own
  subsystems; a requirement covering all seventeen would be a survey.

## A note on ordering

The goal put the durable API repository before this. The dependency runs the
other way: a repository over the canonical plane reads canonical tables, and
none existed. Building it first would have meant either reading from nothing or
inventing a parallel schema so that step could come first. The two steps keep
their content and swap places.

## What is still open

- **Nothing runs a pipeline into this table.** The sink fits the builder's hook;
  starting a process that fills it is deployment work.
