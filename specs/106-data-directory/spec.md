---
traces: [REQ-WP-065]
status: draft
---

# Feature Specification: The stack's data lives in a directory you choose

**Feature Branch**: `wp-065-data-directory`

**Created**: 2026-09-13

**Status**: Draft

**Input**: REQ-WP-065 — the stack's state moves out of Docker named volumes.

## Context

The named volumes already survived rebuilds; what they could not do is live on a
disk the operator chose or be copied with ordinary tools. Ownership is the whole
difficulty, and Docker Desktop on macOS hides it: all five services report a
bind mount writable whatever owns it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The data is a directory (Priority: P1)

**Acceptance**: every stateful service writes under `CHANNELFLOW_DATA_DIR`, and
a fresh checkout works with no variable set.

### User Story 2 - A server puts it on its own disk (Priority: P1)

**Acceptance**: setting the variable moves every service's state, with no edit
to the compose file.

### User Story 3 - A directory the service cannot write is reported (Priority: P1)

**Acceptance**: `make data-dirs` probes each directory as the service's own
user and names the service and uid when it fails.

### Edge Cases

- macOS cannot reproduce the failure this prevents.
- `du` disagrees across filesystems; content is what settles a migration.
- A leftover named volume would look identical until the disk moved.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Five bind mounts under `${CHANNELFLOW_DATA_DIR:-./data}`.
- **FR-002**: No named volume remains.
- **FR-003**: `prepare` creates and chowns; `verify` probes as the service user.
- **FR-004**: The service table and the compose file are cross-checked.
- **FR-005**: The parser fails rather than matching nothing.
- **FR-006**: `data` is git-ignored and excluded from build contexts.

### Key Entities

- **Service** — name, directory, mount point, uid, gid.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All seven services start healthy on bind mounts.
- **SC-002**: Content checksums match across all five migrated directories.
- **SC-003**: The API reads the migrated catalog.
- **SC-004**: A shape change in the compose file fails the parser guard.

## Assumptions

- The operator runs `make data-dirs` before the first start; the deployment
  document says so.

## Open Questions

- Integration tests leave a `cex_trades_<hash>` table per run; 156 had
  accumulated. Cleanup is not part of this.
