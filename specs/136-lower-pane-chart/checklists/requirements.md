# Specification Quality Checklist: The lower pane is a chart on the main chart's time axis

**Created**: 2026-10-04
**Feature**: [spec.md](../spec.md)

- [x] The facts that decide the design are read from the code and the installed typings (index axis over the union of times; the candles at close; the library has the sync APIs; the existing tests' contract)
- [x] Requirements testable (SC-001, SC-002 data; SC-003 sync; SC-004 measured in a browser)
- [x] Scope bounded (no v5, no hole-marking, no new data)
- [x] Edge cases identified (boundary instant, forming bar, echo, unmount order, resize)
- [x] No [NEEDS CLARIFICATION] markers

## Notes

Index alignment is the whole feature and is what the whitespace backbone is for; the screenshot is the check no unit test can stand in for.
