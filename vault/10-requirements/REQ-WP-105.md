---
id: REQ-WP-105
title: "Compaction rewrites what arrived since the last pass, not the whole table"
type: work-package
prd_ref: "§36, §29.0; measured 2026-10-13"
prd_lines: "6034-6052"
phase: null
status: implemented
depends_on: [REQ-WP-100, REQ-WP-104, REQ-WP-068]
tags: [lakehouse, compaction, performance]
hard_gated: false
---

## Requirement

[[REQ-WP-104]] made maintenance hourly, because files accumulate all day and a read costs a request per file. The first pass of
that kind took **1,612 seconds for the features table**: compaction rewrote every live row into one file, so the cost of a pass was
the size of the table (1.3 million rows) however little had arrived -- to fold 68 small files into a file that did not need touching.
At an hour's interval that is most of the host's I/O spent on nothing.

Compaction now merges only **the small files after the last large one** -- a large file being one of `BIG_FILE_ROWS` (100,000) rows or
more, which a previous pass made. The cost of a pass is what arrived since the last. Order is the contract and is kept: the tail is
contiguous in commit order, the new file is ordered as the newest file it replaced ([[REQ-WP-100]]), and a small file before a large
one is never merged with files after it. One file is not worth a snapshot.

## Acceptance

- A large file is left in place and the small files after it are merged into one (tests).
- Rows come back in the order they went in, also after a later append and a second pass (tests).
- A second pass merges only what arrived since the first and rewrites no earlier file (test).
- A table whose files are all small is merged whole, as before; a single small file after a large one is not rewritten (tests).
- A small file before a large one is not merged across it (test).
- On the running stack the next maintenance pass over the features table takes seconds, not tens of minutes.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-157-compact-the-tail]]
- **Tests:**
    - `tests/unit/lakehouse/test_iceberg.py::test_a_large_file_is_left_alone_and_only_the_small_ones_after_it_are_merged`
    - `tests/unit/lakehouse/test_iceberg.py::test_a_second_pass_merges_only_what_arrived_since_the_first`
    - `tests/unit/lakehouse/test_iceberg.py::test_a_small_file_before_a_large_one_is_not_merged_across_it`
    - `tests/unit/lakehouse/test_iceberg.py::test_a_table_whose_files_are_all_small_is_merged_whole_as_before`
    - `tests/unit/lakehouse/test_iceberg.py::test_one_small_file_after_a_large_one_is_not_worth_a_snapshot`
    - `tests/unit/lakehouse/test_iceberg.py::test_rows_come_back_in_the_same_order_when_only_the_tail_was_merged`
    - `tests/unit/lakehouse/test_iceberg.py::test_the_default_leaves_a_table_of_a_hundred_thousand_rows_alone`
- **Code:**
    - `src/channelflow/lakehouse/iceberg.py`
- **Outcomes:** [[OUT-2026-10-13-implement-compact-the-tail]]
<!-- trace:end -->
