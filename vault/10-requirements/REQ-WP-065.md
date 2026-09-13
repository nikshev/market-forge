---
id: REQ-WP-065
title: The stack's data lives in a directory you choose
type: work-package
prd_ref: "§6.2, §7, §45 Phase 8"
prd_lines: "405-420, 770-782, 6904-6913"
phase: 8
status: implemented
depends_on: [REQ-WP-064, REQ-WP-056]
tags: []
---

## Requirement

Every stateful service in the stack writes to a Docker named volume:
`postgres_data`, `minio_data`, `redpanda_data`, `prometheus_data`,
`grafana_data`. Those already survive a rebuild, a `down` and a restart, and are
destroyed only by `make reset`. **The problem they have is not durability.**

A named volume lives inside Docker's own storage. On a server the data belongs
on a disk the operator chose — a mounted volume, a backed-up path — and it has
to be copyable with ordinary tools. A named volume is neither.

So the stack takes a directory: `CHANNELFLOW_DATA_DIR`, `./data` in development
and whatever the server mounts in production, without editing the compose file.

### Ownership is the whole difficulty, and it is invisible here

A named volume is initialised by Docker, which copies the image's ownership onto
it. **A bind mount is not.** The host directory keeps the ownership it has, and
each image runs as a different user:

    postgres     root, and its entrypoint chowns and drops to postgres
    minio        root
    redpanda     uid 101
    prometheus   uid 65534
    grafana      uid 472

On Linux a directory those users cannot write is a container that fails to
start, or worse, one that starts and cannot persist.

**This cannot be observed on the development machine.** Docker Desktop on macOS
maps bind-mount access onto the host user, so every one of the five reports the
directory writable whatever its ownership — measured, all five `WRITABLE`,
including uid 65534 into a directory owned by someone else. The failure appears
only on the server this change exists to serve.

So the ownership is prepared explicitly rather than assumed, by a step that runs
the same way on both platforms, and the deployment document says what it is for.

### The data that exists already

The current volumes hold 46 MB of PostgreSQL and 165 MB of object store. A
change that left them behind would look like it worked and lose a warehouse, so
moving them is part of this and not an afterthought for the operator.

## Acceptance

- Every stateful service mounts `${CHANNELFLOW_DATA_DIR}/<service>`, with a
  default that works in a fresh checkout.
- One command creates the directories with the ownership each image needs, and
  works identically on macOS and Linux.
- A directory the service cannot write is reported before the stack starts,
  naming the service and the user it runs as — rather than surfacing as a
  container that restarts.
- The existing named volumes' contents are moved, and the move is verified by
  comparing what the stack serves afterwards, not by the copy reporting success.
- `CHANNELFLOW_DATA_DIR` is documented, ignored by git, and absent from the
  build context.
- The deployment document describes the directory, the ownership step and what
  to back up.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-106-data-directory]]
- **Tests:**
    - `tests/unit/deploy/test_data_dir.py::test_every_stateful_service_writes_into_the_data_directory`
    - `tests/unit/deploy/test_data_dir.py::test_no_named_volume_remains`
    - `tests/unit/deploy/test_data_dir.py::test_the_data_directory_is_never_committed_or_built_into_an_image`
    - `tests/unit/deploy/test_data_dir.py::test_the_directory_is_a_variable_so_a_server_needs_no_edit`
    - `tests/unit/deploy/test_data_dir.py::test_the_mount_points_agree_with_the_compose_file`
    - `tests/unit/deploy/test_data_dir.py::test_the_parser_fails_rather_than_finding_nothing`
    - `tests/unit/deploy/test_data_dir.py::test_the_users_are_the_ones_the_images_run_as`
- **Code:**
    - `tools/deploy/data_dir.py`
- **Outcomes:** [[OUT-2026-09-13-implement-data-directory]]
<!-- trace:end -->

## Notes

This is deliberately done before the ingest daemon. Data collected into named
volumes would have to be moved again, and a migration is cheaper when the thing
being moved is 200 MB of test data rather than a month of market history.
