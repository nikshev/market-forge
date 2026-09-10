---
id: SPEC-068-derivatives-panes
requirement: REQ-WP-030
speckit_path: specs/068-derivatives-panes/spec.md
status: draft
---

## Summary

[[REQ-WP-027]] built three of PRD §27.3's nine panes and deferred four to Phase
3 in writing. Phase 3's data is finished, so the four entries are trivial.

**What is not trivial is that a pane can name a feature nobody registers.** Such
a pane renders "no readings of this feature" forever — a message this
application produces honestly for a real absence — and a reader cannot tell a
typo from a quiet market. The list will grow to nine and beyond, edited by people
who are not looking at the registry.

So this is mostly about a check, and the check has to cross languages: the panes
are TypeScript and the registry is Python. Either side alone would compare a list
against itself.

One thing is named rather than hidden: nothing writes derivative features into
the feature table yet. A pane over an empty table says "no feature points in this
window", which is honest and will look like a bug to whoever opens it first.

## Links

- Requirement: [[REQ-WP-030]]
- The road it is the second load on: [[REQ-WP-027]]
- The features it names: [[REQ-WP-013]]
