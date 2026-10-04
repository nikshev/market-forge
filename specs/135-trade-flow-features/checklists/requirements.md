# Specification Quality Checklist: CVD from bars

**Created**: 2026-10-04
**Feature**: [spec.md](../spec.md)

- [x] Facts that decide the design are read from the code (the bars table already stores the aggressor split and trade ids; resample sums them over complete windows; the worker already reads every series)
- [x] The deviation from the PRD (base units, not notional) is stated, recorded in an ADR, and reversible
- [x] Requirements testable (SC-001 numbers; SC-002 look-ahead; SC-003 gap; SC-004 idempotence)
- [x] Scope bounded (no book, derivatives, profile, divergence, notional split, backfill beyond the bars)
- [x] Edge cases identified (zero volume, forming bar, id-span mismatch, non-sequential venues, corrected bar)
- [x] No [NEEDS CLARIFICATION] markers

## Notes

SC-005 is measured before the id-span check is relied on; if live bars do not satisfy it, that clause is dropped.
