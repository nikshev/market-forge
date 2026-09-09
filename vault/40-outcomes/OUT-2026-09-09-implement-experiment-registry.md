---
id: OUT-2026-09-09-implement-experiment-registry
step: implement
records: [REQ-REPRO-001, REQ-BIAS-011]
commit: null
---

## What was done

`channelflow.experiments`: the four-component run identity, canonical hashing
for the config and the dataset, the registry as a lakehouse table, and the gate
between a run and a reportable result. 43 unit tests, 27 mutations attempted.

## Three components, and what happens when one is missing

PRD §0 item 13 names four. [[ADR-053]] built the dataset hash; this is the other
three. The design work was not in computing them — it was in the three failure
modes that look identical in a record of four strings:

- a run that fits no model, so there is no artifact and never was one;
- a run that fitted one and nobody recorded the artifact;
- a commit taken from a working tree with uncommitted changes.

The first is reproducible. The other two are not, and the third is the one that
happens by accident and looks most convincing: `git rev-parse HEAD` answers
cheerfully in a dirty tree, the hash resolves, the commit exists, and the code
that ran is gone. So each component is present or explicitly absent, the absence
says which kind it is, and every missing component is named at once rather than
one per re-run.

## Storage is not enforcement

PRD §41 rule 11 asks that discarded variants be stored "to reduce silent
cherry-picking". A registry alone does not do that, and it is worth being exact
about why: nobody can verify what someone considered and never wrote down. A
registry that is merely available is an honour system with a database attached.

What is verifiable is a claim about a field. Reporting a winner means naming the
variants it beat, and every one of them has to already be on record. Cherry-
picking then requires lying about the field rather than staying quiet about a
variant. [[ADR-054]] records that, and the module states the limit in its own
docstring — this cannot stop someone who never mentions a variant; it stops the
one that was run, lost and quietly dropped, which is the case rule 11 is about.

Recording is unconditional in the other direction: an unreproducible run is
recorded, as unreproducible, with the reason in its row. Refusing to record it
would leave no trace of it at all, which is the outcome rule 11 is against.

## What the sweep found, and what it did not

Twenty-seven mutations attempted; twenty-six were behavioural and all
twenty-six were caught. One real gap:

**The run hash concatenated its components without framing them.** A run over
dataset `ab` with config `c` hashed identically to one over dataset `a` with
config `bc` — two different runs sharing an identity, and the pair that would
collide in practice is a dataset hash and a config hash whose boundary moved by
a character. Each component is length-prefixed now and a test pins the
collision.

**Two of the twenty-seven were not mutations.** Removing the integer type tag
alone, or the string tag alone, changes no hash: the remaining tag still
separates the two encodings. Removing *both* collides `60` with `"60"`, and
`test_a_number_written_as_a_string_is_not_the_same_config` catches that — which
was verified directly rather than assumed. The property is tested; the
single-tag edits simply were not behavioural changes, and reporting them as
survivors would have overstated the gap.

## What was decided

- **The registry is a lakehouse table.** It inherits an immutable history and
  atomic commits without asking, and a registry that could be tidied up after
  the fact would defeat the rule it exists to enforce.
- **Its event-time column is the experiment's own as-of instant**, not a clock
  reading, so two replays of one study produce identical rows and the registry
  answers a point-in-time read like every other table on the plane.
- **An absence round-trips as an absence**, not as a string that reads like one:
  a caller comparing against `ModelAbsence.NO_MODEL` gets the answer rather than
  a near miss.
- **Nothing here reads a clock or shells out to git**, asserted by two import
  bans. The commit and the dirty flag are supplied.
- **The lakehouse's isolation ban now covers this package too.** It sits on the
  canonical plane, so a domain module importing it would pull pyarrow, duckdb
  and boto3 in behind it.

## Mutation results

Twenty-six behavioural mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| A dirty tree is reproducible | `test_a_commit_from_a_dirty_tree_is_not_reproducible` |
| An unrecorded artifact is reproducible | `test_a_model_whose_artifact_nobody_recorded_is_not_reproducible` |
| A run with no model is called irreproducible | `test_a_run_that_fits_no_model_is_still_reproducible` |
| Only the first gap is reported | `test_every_missing_component_is_named_at_once` |
| An abbreviated commit is accepted | `test_an_abbreviated_or_invented_commit_is_refused` |
| An empty dataset or config is accepted | `test_a_run_with_no_dataset_or_no_config_is_refused_outright` |
| The run hash ignores the dirty flag | `test_a_dirty_run_is_not_the_same_run_as_its_commit` |
| The run hash is not framed | `test_a_component_cannot_borrow_a_character_from_the_next_one` |
| Config keys are not sorted | `test_a_config_hashes_the_same_however_it_was_written_down` |
| A bool hashes as an int | `test_a_quoted_flag_is_not_the_same_config_as_an_unquoted_one` |
| Both type tags dropped | `test_a_number_written_as_a_string_is_not_the_same_config` |
| An unencodable value falls back to repr | `test_a_config_holding_something_unencodable_is_refused` |
| A non-string config key is coerced | `test_a_non_string_key_is_refused` |
| The dataset reference ignores the content hash | `test_a_dataset_reference_changes_with_the_snapshot_and_with_the_content` |
| The dataset reference is order dependent | `test_a_dataset_reference_does_not_depend_on_the_order_of_its_tables` |
| A reference over no tables is allowed | `test_a_dataset_reference_over_no_tables_is_refused` |
| A table with no content hash is accepted | `test_a_table_referenced_without_a_content_hash_is_refused` |
| Only kept runs are recorded | `test_a_discarded_variant_is_recorded_exactly_like_a_kept_one` |
| An unreproducible run is refused instead of recorded | `test_an_unreproducible_run_is_recorded_rather_than_refused` |
| The reason is dropped from the row | `test_an_unreproducible_run_is_recorded_rather_than_refused` |
| An absence reads back as a plain string | `test_an_absence_reads_back_as_an_absence` |
| An unnamed variant is accepted | `test_a_run_without_a_variant_name_is_refused` |
| The gate skips the reproducibility check | `test_an_irreproducible_result_cannot_be_reported` |
| The gate does not check the registry | `test_a_variant_that_lost_and_was_never_recorded_stops_the_report` |
| A winner outside its own field is accepted | `test_a_winner_that_is_not_in_its_own_field_is_refused` |
| A duplicated variant is accepted | `test_a_field_that_counts_a_variant_twice_is_refused` |

## A validator rule had to change

Promoting `REQ-PHASE-6` fired R8: a requirement at `implemented` needs a source
file carrying its marker, and no module implements a phase. R8 was written for
work packages, and until today no phase had ever left `draft`, so the case had
never come up.

The finding is not that Phase 6 failed to earn the status. It is that
`implemented` was unreachable for an entire requirement type, permanently — the
`covers:` machinery added the same day exists to make a phase promotable, and R8
made the top rung unreachable whatever was built.

[[ADR-055]] records the fix: `covers:` becomes a `COVERS` edge and R8 follows it,
so a roll-up has code when every requirement it covers has code. `all`, not
`any`; and a phase covering nothing still has none, which is the right answer
for PRD §45's Phase 8. Four mutations cover the new behaviour, because both of
those readings are how this could quietly become an exemption.

The ADR says plainly that the rule was changed while it was blocking a status I
wanted, and why the reasoning stands without that.

## What is still open

- **`REQ-BIAS-011` is `specified`, not `implemented`.** The mechanism exists and
  nothing publishes through it. Marking it implemented on the strength of an
  unused gate would claim the coverage [[ADR-024]] refused to claim for rule 2
  on the strength of one engine's guard, and the same refusal applies here.
- **None of the seventeen research modules reports through the gate.** Each
  adoption is its own step and each will need its own dataset reference —
  most of them currently read fixtures rather than tables.
- **PRD §30's PostgreSQL `experiments` table is unanswered.** That is a control-
  plane question; §29.B's lineage question is what this answers.
- **A config's floats hash by their IEEE-754 bytes**, so `-0.0` and `0.0` are
  different configs. That is the same conservative reading [[ADR-053]] takes for
  data, and it will surprise someone eventually.
