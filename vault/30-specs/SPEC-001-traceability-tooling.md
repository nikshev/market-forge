---
id: SPEC-001-traceability-tooling
requirement: REQ-INFRA-001
speckit_path: specs/001-traceability-tooling/spec.md
status: draft
---

## Summary

Specifies the traceability graph and coverage validator already built in
Tasks 4-10: collectors that turn vault notes, Spec Kit specs, pytest
collection and `# @trace:` source comments into a typed graph, seven
validator rules over it, a dashboard/note writer that only ever touches text
between marker pairs, and a `show` command for one requirement at a time. The
authoritative text lives in the Spec Kit spec at `speckit_path`; this note
exists so the spec appears in the Obsidian graph.

## Links

- Requirement: [[REQ-INFRA-001]]
