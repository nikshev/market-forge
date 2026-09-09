---
id: OUT-2026-09-09-plan-lakehouse-repository
step: plan
records: [REQ-STORE-002]
commit: null
---

## What was done

Four table modules, one repository, one conformance suite. 10 tasks.

## What was decided

- **Three container types on the plane rather than six child tables.** §29.6
  names "forecast arrays" and "quality components"; Arrow and Parquet carry
  lists and maps natively and both query engines read them.
- **A transition history keeps a child table**, because §29.7 asks for a core
  plus a separate table and because four parallel lists only mean anything read
  together, in an order nothing enforces.
- **No `cap` column on a contribution.** A group's cap is a §22.1 constant, not
  a property of one contribution, and storing it would be a second source of
  truth a reader could believe over the constant.

## What is still open

- Nothing from this step.
