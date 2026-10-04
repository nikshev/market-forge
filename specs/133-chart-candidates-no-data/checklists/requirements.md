# Specification Quality Checklist: The chart hides candidate extrema until asked; a pane with no data says so

**Created**: 2026-10-04
**Feature**: [spec.md](../spec.md)

- [x] The facts that decide the design are read from the code and written down (one series carries every feature; `paneSeries` has three states; the link vocabulary is §27.2's)
- [x] Requirements testable (SC-001 counts marks; SC-002 counts buttons in each series state)
- [x] Success criteria measurable
- [x] Scope bounded (no feature producer, no API change, no deep-link change)
- [x] Edge cases identified (zero is data, gaps are not "no data", failure is not absence, refetch with the switch on)
- [x] No look-ahead by construction: the switch widens the view, never the instant (FR-003)
- [x] No [NEEDS CLARIFICATION] markers

## Notes

"No data" is for the loaded view, and says so. That is an assumption, written under Assumptions, because the
alternative (ask the API about all time) needs an endpoint nobody has asked for.
