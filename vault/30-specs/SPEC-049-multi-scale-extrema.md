---
id: SPEC-049-multi-scale-extrema
requirement: REQ-EXP-016
speckit_path: specs/049-multi-scale-extrema/spec.md
status: draft
---

## Summary

EXP-016 asks whether nesting a candidate inside a higher timeframe improves it,
and ends with the sentence that shapes the whole module: "measure incremental
value, not visual appeal".

Multi-scale confluence is the most visually convincing idea in technical
analysis. A chart of the candidates that survived three timeframes agreeing
looks obviously better than a chart of all of them, because every survivor is a
good-looking trade and the ones the filter removed are not on the page. So each
rule here reports two numbers: the change in the average trade, which a filter
improves almost by definition, and the change in the total, where a selective
rule usually loses because it removed winners along with losers. The reading
names that case and the report lists the rules in it.

The other thing a picture cannot show is *when* the higher timeframe was known.
A five-minute candidate at 10:07 sits inside a fifteen-minute bar that closes at
10:15, and that bar's zone is partly made of what happened after the candidate.
Only frames that had closed are visible, and frames out of closing order are
refused — out of order, "the last frame that had closed" is whichever one
happened to be last in the list.

## Links

- Requirement: [[REQ-EXP-016]]
- Builds on: [[REQ-WP-019]], [[REQ-BT-001]], [[REQ-CHAN-001]]
