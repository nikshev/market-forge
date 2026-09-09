---
id: SPEC-045-derivative-turning
requirement: REQ-EXP-012
speckit_path: specs/045-derivative-turning/spec.md
status: draft
---

## Summary

EXP-012 compares four causal slope estimators — the raw trailing return sign
change, causal local polynomials of order 2 and 3, and a Kalman filtered slope —
against labels made by a centred filter, at horizons of 3, 6, 12 and 24 bars.

The line the experiment ends on is the one this module could most easily cross:
centred filters are label references, never live candidates. A centred filter is
the best turning-point detector here precisely because it sees both sides of the
turn, and that is what disqualifies it — its answer at bar `t` changes when bar
`t + 1` arrives. So the labeller declares `centered = True` and every candidate
goes through [[REQ-NRT-D]]'s own `require_causal` before the comparison starts.
The declaration is the guard; a comment would not be.

The same care decides where a local polynomial is read. Fitted to a window and
evaluated at its right edge it is causal; evaluated at its centre it is the same
arithmetic and forbidden. Past a turn the two disagree in sign, which is how a
test can tell them apart.

Precision, not recall: a method that calls every bar a turn has perfect recall
and no information. A method that calls nothing has no precision at all —
absent, not zero.

## Links

- Requirement: [[REQ-EXP-012]]
- Builds on: [[REQ-WP-019]], [[REQ-NRT-D]]
