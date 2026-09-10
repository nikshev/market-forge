# Contract — the pane check

```
parse_panes(source) -> list[str]     # raises PaneListUnreadable
offered_features() -> list[str]      # parse_panes(panes.ts)
```

## Guarantees

- every offered feature is a registered feature name, or the suite fails naming
  the offender;
- a source that no longer declares `PANES` as a list is a failure, not an empty
  answer;
- a `PANES` list with no entries is a failure, for the same reason.

## Does not

Validate labels, ordering or layout. Nine buttons on one row is a layout
question and not a correctness one.
