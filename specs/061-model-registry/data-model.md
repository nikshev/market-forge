# Phase 1 — Data model

## `Registration` — PRD §23.9's eleven

`model_type`, `feature_set_versions`, `train_start_ns`/`train_end_ns`,
`validation_start_ns`/`validation_end_ns`, `code_commit`, `hyperparameters`,
`scaler_parameters`, `calibration_model`, `metrics`, `artifact_hash`,
`deployment_status`.

Refused: an empty named string; an empty `feature_set_versions`,
`hyperparameters` or `metrics`; a span that ends before it starts; a validation
span that starts before training ends.

That last one is PRD §41 rule 10 in a constructor — a model validated on rows it
was trained on is not validated, and the number it reports is the one the rule
exists to stop.

## `model_registry` table

One row per registration. The three mappings are JSON strings rather than typed
columns: their keys belong to the caller, and a feature set nobody has invented
yet must not require a schema change — which would change the fingerprint of
every dataset citing this table.

`artifact_hash` is the identity. Two rows sharing it describe one artifact, which
is what makes the [[ADR-056]] watermark exact rather than heuristic.
