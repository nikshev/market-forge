---
id: OUT-2026-09-13-implement-data-directory
step: implement
records: [REQ-WP-065]
commit: null
---

## What was done

Five named volumes became bind mounts under `CHANNELFLOW_DATA_DIR`,
`tools/deploy/data_dir.py` prepares and checks them, and the existing 200 MB was
moved. 7 tests.

## The problem was not durability

The named volumes already survived a rebuild, a `down` and a restart; only
`make reset` destroyed them. What they could not do is live on a disk the
operator chose, or be copied with ordinary tools — which is what moving to a
server requires.

## Ownership is the whole difficulty, and the development machine hides it

Docker initialises a named volume by copying the image's ownership onto it. A
bind mount keeps whatever the host directory has, and the five images run as
five different users: root, root, 101, 65534, 472.

**Measured before deciding anything: on this Mac all five report the directory
writable, whatever owns it.** Docker Desktop maps bind-mount access onto the
host user, so uid 65534 writes into a directory owned by somebody else and
reports success. The failure this change exists to prevent cannot be reproduced
on the machine the change was written on.

So the ownership is prepared by a step that runs identically on both platforms,
and `verify` probes each directory **as the user the service is** rather than as
whoever ran the command — a check run as the operator would pass everywhere and
prove nothing, which is the same illusion Docker Desktop already provides.

## The migration was verified by content, not by the copy

`du` reported the object store shrinking from 169 MB to 72 MB, which looks
exactly like a truncated warehouse. It was not: 16,596 files on both sides, and
an md5 over every file's contents identical on both. The difference is block
accounting — many small files, ext4 inside the Docker VM against APFS through
virtiofs.

Accepting the copy's exit code would have accepted a real truncation on a day
when there was one. All five directories were compared the same way, and all
five match.

## What the catalog turned out to hold

156 tables, every one of them `cex_trades_<hash>` — leftovers from integration
test runs, which create a uniquely named table each time and never drop it. They
are what the 165 MB was. Not a defect of this change, and not harmful on a
server where tests do not run, but worth knowing before someone reads the number
as market data.

## Afterwards

All seven services start healthy on the bind mounts, including the three with
non-root users, and the API reads the migrated catalog and answers
`/readyz` with `the catalog answered`.
