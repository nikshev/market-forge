---
id: SPEC-142-signal-notary-contract
requirement: REQ-INFRA-006
speckit_path: specs/142-signal-notary-contract/spec.md
status: draft
---

## Summary

A minimal write-once notary contract (`commit`, `resolve`, one owner) for Monad testnet, its offline tests, a
deploy script that refuses the wrong chain, and a read-back verification of the recorded deployment. The
contract keeps the committer-supplied bar close time and the chain's block time as two separate values.
The authoritative text lives in the Spec Kit spec at `speckit_path`.

## Links

- Requirement: [[REQ-INFRA-006]]
