---
id: SPEC-143-notarize-final-records
requirement: REQ-INFRA-007
speckit_path: specs/143-notarize-final-records/spec.md
status: draft
---

## Summary

After a record becomes final, hash it together with the config hash, the input dataset version and the code
commit, and commit it through the deployed notary — asynchronously, with a visible outbox, for final channel
snapshots and for decisions including NO ALERT. A reader can verify any record against the chain, and the
product states the measured bar-close-to-block latency rather than "before the move". The authoritative text
lives in the Spec Kit spec at `speckit_path`.

## Links

- Requirement: [[REQ-INFRA-007]]
- Builds on: [[REQ-INFRA-006]]
