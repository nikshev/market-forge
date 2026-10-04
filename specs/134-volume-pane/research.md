# Research: the volume pane

## R1. Where volume comes from
**Decision**: the bars the page already loads (`BarOut.volume_base`, final bars only).
**Why**: it is a property of the bar; the API already serves it; no producer, feed or field is needed.
**Alternatives**: a `volume` feature in the features table (needs a writer that does not exist and duplicates
a number the bar has); quote volume (not on the bar).

## R2. How the pane list stays honest
**Decision**: `BAR_PANES` beside `PANES`.
**Why**: `test_pane_features.py` ties `PANES` to the feature registry; volume is not a feature.

## R3. Availability
**Decision**: Volume is in the available set when a final bar exists; the feature series' state does not affect it.
**Why**: the owner's complaint was panes with nothing behind them; the one pane with data must not wait on a
request that can fail.
