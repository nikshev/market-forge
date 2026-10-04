# Data model: candidates off by default, "no data" panes

No stored data and no API shape changes. The view state is:

| Name | Type | Where | Default | Notes |
|---|---|---|---|---|
| `showCandidates` | boolean | `App` state → `Chart` prop | `false` | Not in the link, not persisted. |
| `pointsLoaded` | boolean | `App` state | `false` | False from the start of a load until the feature series answers (ok or failed). |
| `available` | `ReadonlySet<string> \| null` | derived in `App` | `null` | `null` = not known (loading or failed). Otherwise the pane features whose `paneSeries` is `ok`. |
| `pane` | `string \| null` | `App` state | first pane with data | `null` when no pane has data. |

State transitions of `pane`: on a change of `available` to a set, `pane ← chooseSelection(pane, available)`;
`null` availability leaves it alone; a pressed pane (only possible when available) sets it directly.

`ExtremaResponse` (`confirmed`, `candidates`) is unchanged and is still fetched whether or not the switch is on,
so turning it on is instant and a refetch while on keeps drawing.
