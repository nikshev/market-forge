---
id: OUT-2026-09-09-implement-training-gate
step: implement
records: [REQ-US-007]
commit: null
---

## What was done

`channelflow.dataset.certified`: a dataset training accepts, obtainable only by
passing both leakage checks. The direct baseline, the derivative experiment and
the ablation now take one. 9 tests, and every existing caller updated.

This closes REQ-US-007, and with it all seven user stories.

## The check existed; the guarantee did not

Nothing in this feature is a new check. `check_rows` and `check_folds` have been
there since [[REQ-WP-017]], with [[ADR-025]] already making an empty dataset fail
rather than pass trivially. What was missing is that nothing required them: a
caller could fold a dataset and fit on it, and the checks would sit in a test
file agreeing with themselves.

The change is which object training accepts. A `CertifiedDataset` cannot be
constructed around an unclean report, so the checks are not a step in a
procedure — they are the constructor.

## Two checks, one fixture

The sweep found that dropping the *fold* report from the certificate's own guard
changed nothing. Every fixture with clean rows also had clean folds, so the two
checks were indistinguishable. They answer different questions: a row can be
individually honest while the split trains on its own validation window, which
is PRD §24.3's rule and the one a fold builder gets wrong rather than a labeller.
The new test builds exactly that — clean rows, a fold containing its own
validation row.

## What was decided

- **The certificate holds its folds**, and training reads them from it. A caller
  who certifies and then edits their own list cannot train on something the
  certificate does not describe.
- **The signature test is structural.** A fifth training entry point fails it by
  existing.
- **The test fixtures certify rather than stub.** A fixture with a leak now fails
  loudly.

## Mutation results

Six mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| An unclean report is accepted | `test_a_certificate_cannot_be_built_around_an_unclean_report` (+1) |
| Only the row report is checked | `test_clean_rows_do_not_certify_contaminated_folds` |
| Only the fold report is checked | `test_a_leaked_label_refuses_and_names_the_rule` (+1) |
| The checks are not actually run | `test_a_clean_dataset_certifies` (+1) |
| The certificate does not hold its folds | `test_a_row_without_a_forward_path_is_refused` (+1) |
| Training reads its folds from elsewhere | `test_the_direct_baseline_reports_metrics_per_fold_and_in_aggregate` |

## What is still open

- **`GMDHNetwork.fit_with_selection` takes arrays.** A caller who assembles them
  by hand bypasses the gate; the entry points that assemble them are gated
  instead. Closing that would mean the estimator knowing about datasets, which
  is the coupling this design avoids.
- **Nothing certifies at ingestion.** The gate is at training, which is where a
  leak turns into a number someone believes.
