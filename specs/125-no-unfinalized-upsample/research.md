# Research: No unfinalized higher-timeframe close reaches a lower-timeframe consumer

## R1. Does `resample` identify minutes or count them?

It counts: `if len(window) != expected` (`pipeline/resample.py`). Probed
(`specs/125-no-unfinalized-upsample/probe.py`): minutes 0,1,2,3,3 produce a bar; so does a window
with one non-final bar. **Decision:** identify (the set of source open times), refuse on missing,
duplicated or not final. *Alternative:* keep counting and add a finality pass — rejected, it leaves
the duplicate hole.

## R2. Can the holes occur on the deployment?

Not today. The `bars` table refuses unfinalized rows on write ([[ADR-005]]); the live table holds
55,546 one-minute rows with 55,546 distinct keys. `read_bars` does not deduplicate, so one duplicate
row — a restarted ingest re-emitting a minute — would reach `resample` as it is. **Decision:** the
function must not depend on another module's behaviour for the property it is cited for.

## R3. What does the as-of read filter on?

`event_time_column="close_time_ns"` in the `bars` schema, so a bar is returned for an instant only
once its window has closed. **Decision:** tested with a resampled bar, at seven instants inside a
window and at its close; and mutated (`open_time_ns`) to show the test would notice.

## R4. Which consumer is on the other side?

None reads two timeframes in one computation (`features/`, `models/`, `channels/` searched).
**Decision:** state the property on the read path; it binds whatever is written later.

## R5. How should a refusal describe duplicates and non-final bars?

Keep `Refusal`'s shape. `present` = distinct minutes present. Keep the existing reason prefix and
append `; missing [...]; duplicated [...]; not final [...]` with open times, so existing assertions
(`present == 4`, the window start in the reason) hold and the new ones can name the minute.
*Alternative:* new fields — rejected, nothing needs them structured yet and the pass already prints
`reason`.

## R6. How long does the suite take, and what is the budget?

160 s for eleven tests against SC-004's 60 s; the day fixture is built and resampled twice. **Decision:**
one stored fixture per module and instants chosen deliberately; the tasks measure it.

## R7. Is there a mutation spec for `resample.py`?

No. The requirement's "caught by the suite and **named**, proven by introducing one" has never been
shown. **Decision:** two specs, one for the function and one for the table's as-of column.
