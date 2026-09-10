# Phase 1 — Data model

## `confirmed_extrema`

Event time `known_at_ns`; `extremum_time_ns` an ordinary column beside it. That
split is the feature.

`prominence_bps`, `prominence_atr`, `channel_class` and `source_candidate_id`
are strings, empty for absent, so an unmeasured prominence and a zero one stay
apart.

## `extremum_candidates`

Event time `observed_at_ns`; `candidate_time_ns` beside it, for the same reason.

## `Extrema`

`confirmed` and `candidates`, two lists. A flag on one list would be a field a
caller can forget to read, and the failure would be a candidate drawn as a
confirmation.

## `ExtremumMarker`

`at_ns`, `kind`, `type`, `price`. The decision module returns markers already
filtered and ordered; the chart maps them to glyphs and does no thinking.
