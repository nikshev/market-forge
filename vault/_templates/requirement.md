---
id: REQ-KIND-000
title: Short imperative title
type: user-story
prd_ref: "§N"
prd_lines: "0-0"
phase: null
status: draft
depends_on: []
tags: []
# hard_gated: set true only for a `type: constraint` note derived from a PRD
# section that mandates a non-waivable correctness test (currently §13A.28's
# non-repainting tests and §41's anti-bias rules; see CLAUDE.md's "rules that
# are not negotiable" section). It gates validator rule R5, which forbids the
# requirement from holding any status past `specified` without a linked test.
# Leave it false (or omit it) for ordinary constraints that restate process
# ("build incrementally") rather than a testable correctness property — the
# 14 REQ-PRIN-* notes are `type: constraint` but not hard_gated for exactly
# that reason. Defaults to false when absent, so get this right on authoring.
hard_gated: false
---

## Requirement

Faithful English statement. Where the PRD gives a formula, threshold or state
machine, reproduce it rather than paraphrasing it.

## Acceptance

- Observable, checkable condition.

## Trace

<!-- trace:begin -->
_Not yet generated. Run `make graph`._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
