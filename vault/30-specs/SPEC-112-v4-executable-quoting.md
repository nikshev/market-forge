---
id: SPEC-112-v4-executable-quoting
requirement: REQ-WP-071
speckit_path: specs/112-v4-executable-quoting/spec.md
status: draft
---

## Summary

PRD §18.8.1 allows `CUSTOM_ACCOUNTING` pools no curve, and until now this system
gave them no price either. The spec makes an executable quote the only way such
a pool is priced, makes a refusal a named outcome rather than a zero, and makes
a mid require both sides — because two of the four measured pools sell without
buying back. Live and replay share one protocol so CI can prove the whole thing
offline against the captured block.

## Links

- Requirement: [[REQ-WP-071]]
