---
id: SPEC-145-derivatives-collector
requirement: REQ-WP-093
speckit_path: specs/145-derivatives-collector/spec.md
status: draft
---

## Summary

The derivatives panes (open interest, funding, basis) are fed by a collector that polls each venue's public derivatives data; the worker writes the features per bar, as of the close. The authoritative text lives in the Spec Kit spec at `speckit_path`.

## Links

- Requirement: [[REQ-WP-093]]
- Decision: [[ADR-070]]
