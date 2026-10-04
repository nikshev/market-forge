# Specification Quality Checklist: The lower panes include volume

**Created**: 2026-10-04
**Feature**: [spec.md](../spec.md)

- [x] The facts that decide the design are read from the code (PANES is checked against the registry; bars carry `volume_base`; availability is REQ-WP-084's)
- [x] Requirements testable (SC-001 counts values; SC-002 counts live panes in three states)
- [x] Success criteria measurable
- [x] Scope bounded (no feature, no API change, `depth_imbalance_10` kept)
- [x] Edge cases identified (zero is data, non-final bar, non-numeric volume, one bar, equal volumes, gaps)
- [x] No [NEEDS CLARIFICATION] markers

## Notes

Whether `depth_imbalance_10` should stay, given §27.3 does not list it, is the owner's call and is left open.
