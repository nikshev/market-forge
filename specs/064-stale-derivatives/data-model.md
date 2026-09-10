# Phase 1 — Data model

No entities. One constant, one exception, one function.

| Name | Meaning |
|---|---|
| `DEFAULT_STALENESS_NS` | five minutes — a research default for venues publishing on a minute cadence |
| `StaleState` | the newest observation is older than the caller accepts as current |
| `require_fresh` | refuses when it is |

`StaleState` is a `LookupError` and deliberately **not** a subclass of
`NoStateAvailable`: a venue that never published and one that stopped are
different facts, and a caller that wants to retry, alarm or fall back needs to
tell them apart.

The default is asserted in a test to be at most an hour, not merely positive. A
thirty-year default is finite and just as vacuous as none.
