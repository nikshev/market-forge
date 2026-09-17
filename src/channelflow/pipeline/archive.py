"""PRD §6.4.4's raw zone: what the venue actually sent, kept.

# @trace: REQ-WP-066
# @trace: REQ-NRT-PARITY

§6.4.4 lays out `s3://channel-flow/raw/cex/...` and line 642 says plainly that
raw immutable payloads "may remain plain compressed objects/Parquet when Iceberg
metadata adds no value". It adds none here: a frame has no schema to evolve, is
never updated, and arrives ten times a second. An Iceberg commit per batch of
those would be metadata larger than the data.

**Why keep them at all.** §7 calls this the source-of-truth tier "where
re-normalization may be required". A parsing mistake found next month can be
repaired over the originals; without them the affected days are simply gone.

Measured on 2026-09-13, one Binance symbol on `aggTrade` and `depth@100ms`:
800 frames a minute, 395 KiB, so **556 MiB a day raw**. gzip at level 6 takes
that to 12.3% -- 68 MiB a day. The compression is what makes the tier
affordable, so it is not optional here.

**Frames are stored uninterpreted.** §6.4.4's example splits the zone into
`cex/trades/` and `cex/book_deltas/`, which would mean reading each payload to
decide where it goes -- normalisation, done by the one component whose purpose is
to be free of it. A frame names its own stream; this archives by venue and
minute and lets the reader route.
"""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

#: One object per minute. At the measured rate that is about 48 KiB compressed:
#: large enough that per-object overhead is noise, small enough that a reader
#: wanting one minute does not fetch an hour.
MINUTE_NS = 60_000_000_000

GZIP_LEVEL = 6


class ObjectStore(Protocol):
    """Somewhere to put an object. Two implementations, one seam.

    The same shape `lakehouse.catalog` uses for its URI: a local directory in a
    test and in CI, S3 in a deployment, and nothing branching on which.
    """

    def put(self, key: str, payload: bytes) -> None: ...


@dataclass(frozen=True)
class LocalObjectStore:
    """A directory. Used by the tests, by CI, and by a single-machine run."""

    root: Path

    def put(self, key: str, payload: bytes) -> None:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)


@dataclass(frozen=True)
class S3ObjectStore:
    """An S3-compatible bucket, which is MinIO here and S3 on a server."""

    bucket: str
    client: object

    def put(self, key: str, payload: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=payload)  # type: ignore[attr-defined]


class ClockWentBackwards(ValueError):
    """A frame arrived earlier than one already buffered.

    Refused rather than sorted: receipt times come from one process reading one
    socket, so a decrease is a broken clock, and an archive silently reordered
    to hide it would be a worse record than none.
    """


@dataclass
class FrameArchive:
    """Buffers frames and writes one compressed object per minute.

    Nothing here reads a clock. The caller supplies each frame's receipt time and
    calls `flush`, for the reason `BarSink` gives: a component that read the
    time would be untestable exactly where its behaviour matters.
    """

    store: ObjectStore
    venue: str
    prefix: str = "raw/cex"

    _minute_ns: int | None = None
    _frames: list[tuple[int, str]] = field(default_factory=list)
    _written: list[str] = field(default_factory=list)
    #: What a partial write already put under each minute's key. A `flush` in
    #: the middle of a minute writes what it has; the frames that arrive after
    #: it belong to the same object, and writing only those would replace the
    #: minute with its own tail ([[REQ-NRT-PARITY]]).
    _held: dict[int, list[tuple[int, str]]] = field(default_factory=dict)

    @property
    def pending(self) -> int:
        return len(self._frames)

    @property
    def written(self) -> tuple[str, ...]:
        return tuple(self._written)

    def add(self, *, received_at_ns: int, frame: str) -> str | None:
        """Buffer a frame, writing the previous minute when this one opens.

        Returns the key written, if this frame closed a minute.
        """
        minute = received_at_ns // MINUTE_NS
        if self._frames and received_at_ns < self._frames[-1][0]:
            raise ClockWentBackwards(
                f"a frame received at {received_at_ns} follows one at "
                f"{self._frames[-1][0]}; one socket cannot deliver backwards"
            )
        written = None
        if self._minute_ns is not None and minute != self._minute_ns:
            closing = self._minute_ns
            written = self.flush()
            # The minute is over; nothing can be appended to it again, so its
            # held copy is released rather than kept for the life of the process.
            self._held.pop(closing, None)
        self._minute_ns = minute
        self._frames.append((received_at_ns, frame))
        return written

    def flush(self) -> str | None:
        """Write what is buffered. `None` when there is nothing.

        Not an empty object: a minute in which the venue said nothing is a fact
        about the venue, and an empty object would be indistinguishable from a
        minute nobody recorded.
        """
        if not self._frames or self._minute_ns is None:
            return None
        minute = self._minute_ns
        key = self.key_for(minute * MINUTE_NS)
        # Everything this minute has had, not only what arrived since the last
        # write. `store.put` replaces an object, so a mid-minute flush followed
        # by more frames in the same minute used to leave the minute holding its
        # own tail -- measured on a live deployment at 45 of 45 minutes short,
        # one of them by 465 frames of 744 ([[REQ-NRT-PARITY]], PRD §35.5).
        whole = self._held.get(minute, []) + self._frames
        body = "\n".join(
            json.dumps({"received_at_ns": at, "frame": frame}, separators=(",", ":"))
            for at, frame in whole
        )
        self.store.put(key, gzip.compress(body.encode(), GZIP_LEVEL))
        self._held[minute] = whole
        self._frames.clear()
        self._minute_ns = None
        self._written.append(key)
        return key

    def key_for(self, minute_start_ns: int) -> str:
        """`raw/cex/<venue>/<YYYY>/<MM>/<DD>/<HH><MM>.jsonl.gz`.

        Dated from the receipt time in UTC, and nested by day so a reader can
        list one day without listing a year.
        """
        seconds = minute_start_ns // 1_000_000_000
        from datetime import UTC, datetime

        at = datetime.fromtimestamp(seconds, tz=UTC)
        return f"{self.prefix}/{self.venue}/{at:%Y}/{at:%m}/{at:%d}/{at:%H%M}.jsonl.gz"


def read_frames(payload: bytes) -> list[tuple[int, str]]:
    """One archived object back into the frames it holds, in order.

    The inverse of `flush`, and the reason the archive is worth having: a replay
    reads exactly what the socket delivered.
    """
    rows = gzip.decompress(payload).decode().splitlines()
    return [(json.loads(row)["received_at_ns"], json.loads(row)["frame"]) for row in rows]
