"""Move the archive objects already written to the layout that names a symbol.

# @trace: REQ-WP-078

Two things were wrong with where the raw archive put frames, and both left objects behind.

**They were filed at the bucket root.** `build_daemon` prefixed the venue and `key_for`
added it again, so Bybit's frames went to `bybit/raw/cex/bybit/...` where nothing reads.

**Their keys named no symbol.** Three Binance processes shared `raw/cex/binance/<date>/<HHMM>`
and `store.put` replaces an object, so each minute holds the frames of whichever symbol
flushed last. Sampled objects each held exactly one.

Both can be repaired from the objects themselves: a process wrote one symbol, so its
frames name it. What cannot be repaired is what was overwritten, and this reports how
much, as a number, per symbol.

    python -m channelflow.pipeline.archive_rekey            # a dry-run: changes nothing
    python -m channelflow.pipeline.archive_rekey --apply

**It lives in `src/` because the application image copies `src/` only**, and it has to run
where the object store's name resolves -- inside the compose network. `maintenance_main`
is the precedent.

Per object, and in this order, because the order is what makes it safe:

1. The key must match a known layout, or it is refused.
2. The frames must name **exactly one** symbol, or it is refused and left where it is.
3. The destination is absent (a move), identical (the source can go), or different (refused:
   a different object is never overwritten).
4. A move is a server-side copy, then a comparison of size and ETag on both ends, and only
   then a delete. An interruption leaves a duplicate and never a gap, and a second run
   finishes it.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from channelflow.pipeline.archive import read_frames

VENUES = ("binance", "bybit", "okx")

_DAY = r"(?P<y>\d{4})/(?P<m>\d{2})/(?P<d>\d{2})/(?P<hhmm>\d{4})\.jsonl\.gz"
#: The layout before this change: `raw/cex/<venue>/<date>/<HHMM>`, no symbol.
_LAYOUT_A = re.compile(rf"^raw/cex/(?P<venue>[^/]+)/{_DAY}$")
#: The layout `build_daemon` actually wrote after REQ-WP-076: venue twice, at the root.
_LAYOUT_B = re.compile(rf"^(?P<venue>[^/]+)/raw/cex/(?P=venue)/{_DAY}$")
#: The layout this change introduces, which a run leaves behind it.
_LAYOUT_C = re.compile(rf"^raw/cex/(?P<venue>[^/]+)/(?P<symbol>[^/]+)/{_DAY}$")


@dataclass(frozen=True)
class ParsedKey:
    venue: str
    day: str
    hhmm: str
    layout: str
    symbol: str | None = None

    def minute(self) -> int:
        """Whole minutes since the epoch, UTC, from the receipt time the key records."""
        y, m, d = (int(part) for part in self.day.split("/"))
        at = datetime(y, m, d, int(self.hhmm[:2]), int(self.hhmm[2:]), tzinfo=UTC)
        return int(at.timestamp()) // 60


def parse_key(key: str) -> ParsedKey | None:
    """Which layout a key is in, or `None` for a key that is in none of them."""
    for layout, pattern in (("A", _LAYOUT_A), ("B", _LAYOUT_B), ("C", _LAYOUT_C)):
        match = pattern.match(key)
        if match:
            groups = match.groupdict()
            return ParsedKey(
                venue=groups["venue"],
                day=f"{groups['y']}/{groups['m']}/{groups['d']}",
                hhmm=groups["hhmm"],
                layout=layout,
                symbol=groups.get("symbol"),
            )
    return None


def destination_key(parsed: ParsedKey, symbol: str) -> str:
    return f"raw/cex/{parsed.venue}/{symbol}/{parsed.day}/{parsed.hhmm}.jsonl.gz"


def symbol_of(venue: str, frame: str) -> str | None:
    """The symbol a frame names, in the configured spelling, or `None`.

    A pong, an acknowledgement, an error, and anything that is not JSON name no symbol
    and are ignored for attribution rather than counted as a second one.
    """
    try:
        data = json.loads(frame)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    if venue == "binance":
        stream = data.get("stream")
        if isinstance(stream, str) and "@" in stream:
            # `btcusdt@aggTrade` is a lower-case label; the configured symbol is upper case.
            return stream.split("@", 1)[0].upper()
    elif venue == "bybit":
        topic = data.get("topic")
        if isinstance(topic, str) and "." in topic:
            return topic.rsplit(".", 1)[1]
    elif venue == "okx":
        arg = data.get("arg")
        if isinstance(arg, dict):
            instrument = arg.get("instId")
            if isinstance(instrument, str) and instrument:
                return instrument
    return None


@dataclass
class MigrationReport:
    applied: bool
    scanned: int = 0
    #: Objects moved (or, in a dry-run, that would move), per `(venue, symbol)`.
    moved: dict[tuple[str, str], int] = field(default_factory=dict)
    already_there: int = 0
    refused: list[tuple[str, str]] = field(default_factory=list)
    _minutes: dict[tuple[str, str], set[int]] = field(default_factory=dict)
    _span: dict[str, tuple[int, int]] = field(default_factory=dict)

    # -- the extent ---------------------------------------------------------

    @property
    def minutes_present(self) -> dict[tuple[str, str], int]:
        """Distinct minutes holding each `(venue, symbol)`, after this run."""
        return {key: len(minutes) for key, minutes in self._minutes.items()}

    @property
    def minutes_expected(self) -> dict[tuple[str, str], int]:
        """Minutes from the venue's first object to its last, for each of its symbols."""
        return {
            (venue, symbol): self._span[venue][1] - self._span[venue][0] + 1
            for (venue, symbol) in self._minutes
        }

    def shortfall(self, venue: str, symbol: str) -> int:
        """How many minutes in the span hold no frame of this symbol."""
        return self.minutes_expected[(venue, symbol)] - self.minutes_present[(venue, symbol)]

    # -- recording ----------------------------------------------------------

    def see(self, parsed: ParsedKey) -> None:
        minute = parsed.minute()
        low, high = self._span.get(parsed.venue, (minute, minute))
        self._span[parsed.venue] = (min(low, minute), max(high, minute))

    def hold(self, venue: str, symbol: str, parsed: ParsedKey) -> None:
        self._minutes.setdefault((venue, symbol), set()).add(parsed.minute())

    def render(self) -> str:
        lines = [
            "applied" if self.applied else "dry-run (nothing was changed; pass --apply to move)",
            f"scanned {self.scanned} object(s); already in place {self.already_there}; "
            f"refused {len(self.refused)}",
            "",
            f"{'venue':8} {'symbol':16} {'moved':>7} {'present':>8} {'expected':>9} {'missing':>8}",
        ]
        for (venue, symbol), expected in sorted(self.minutes_expected.items()):
            lines.append(
                f"{venue:8} {symbol:16} {self.moved.get((venue, symbol), 0):>7} "
                f"{self.minutes_present[(venue, symbol)]:>8} {expected:>9} "
                f"{self.shortfall(venue, symbol):>8}"
            )
        lines += [
            "",
            "'missing' is the extent of what was overwritten: minutes between the venue's first",
            "and last archived object that hold no frame of that symbol. It is a lower bound --",
            "it cannot see minutes before the first object or after the last.",
        ]
        if self.refused:
            lines += ["", "refused, and left where they are:"]
            lines += [f"  {key}: {reason}" for key, reason in self.refused]
        return "\n".join(lines)


def _is_missing(error: Exception) -> bool:
    """An absent key, whether the client is boto3's or a fake."""
    if type(error).__name__ in {"NoSuchKey", "NotFound"}:
        return True
    response = getattr(error, "response", None)
    code = response.get("Error", {}).get("Code") if isinstance(response, dict) else None
    return code in {"404", "NoSuchKey", "NotFound"}


def _head(client: Any, bucket: str, key: str) -> tuple[int, str] | None:
    try:
        head = client.head_object(Bucket=bucket, Key=key)
    except Exception as error:
        if _is_missing(error):
            return None
        raise
    return int(head["ContentLength"]), str(head["ETag"])


def _list(client: Any, bucket: str, prefix: str) -> list[str]:
    keys: list[str] = []
    token: str | None = None
    while True:
        more = {"ContinuationToken": token} if token else {}
        page = client.list_objects_v2(Bucket=bucket, Prefix=prefix, **more)
        keys.extend(item["Key"] for item in page.get("Contents", ()))
        token = page.get("NextContinuationToken")
        if not token:
            return keys


def rekey(
    client: Any,
    bucket: str,
    *,
    venues: Sequence[str] = VENUES,
    apply: bool = False,
) -> MigrationReport:
    """Place every object under the symbol its own frames name. A dry-run unless `apply`."""
    report = MigrationReport(applied=apply)
    for venue in venues:
        for prefix in (f"raw/cex/{venue}/", f"{venue}/raw/cex/{venue}/"):
            for key in _list(client, bucket, prefix):
                report.scanned += 1
                parsed = parse_key(key)
                if parsed is None:
                    report.refused.append((key, "key matches no known layout"))
                    continue
                report.see(parsed)
                if parsed.layout == "C":
                    assert parsed.symbol is not None
                    report.hold(venue, parsed.symbol, parsed)
                    continue
                _place(client, bucket, key, parsed, report, apply=apply)
    return report


def _place(
    client: Any,
    bucket: str,
    key: str,
    parsed: ParsedKey,
    report: MigrationReport,
    *,
    apply: bool,
) -> None:
    try:
        body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
        frames = [frame for _, frame in read_frames(body)]
    except Exception as error:
        report.refused.append((key, f"object is not readable: {type(error).__name__}"))
        return

    symbols = {s for s in (symbol_of(parsed.venue, frame) for frame in frames) if s}
    if not symbols:
        report.refused.append((key, "no attributable frame"))
        return
    if len(symbols) > 1:
        report.refused.append((key, f"several symbols: {sorted(symbols)}"))
        return
    (symbol,) = symbols

    destination = destination_key(parsed, symbol)
    try:
        source_state = _head(client, bucket, key)
        destination_state = _head(client, bucket, destination)
        if source_state is None:
            report.refused.append((key, "the object vanished while it was being read"))
            return

        if destination_state is not None:
            if destination_state != source_state:
                report.refused.append((key, "destination holds different bytes"))
                return
            report.already_there += 1
            report.hold(parsed.venue, symbol, parsed)
            if apply:
                client.delete_object(Bucket=bucket, Key=key)
            return

        if apply:
            client.copy_object(
                Bucket=bucket, Key=destination, CopySource={"Bucket": bucket, "Key": key}
            )
            if _head(client, bucket, destination) != source_state:
                # Our own bad copy, at a key that was empty a moment ago: remove it so a
                # later run does not meet it as "a destination holding different bytes".
                client.delete_object(Bucket=bucket, Key=destination)
                report.refused.append((key, "copy did not verify"))
                return
            client.delete_object(Bucket=bucket, Key=key)
        report.moved[(parsed.venue, symbol)] = report.moved.get((parsed.venue, symbol), 0) + 1
        report.hold(parsed.venue, symbol, parsed)
    except Exception as error:
        # Whatever state this left is a duplicate and not a gap, and a second run converges.
        report.refused.append((key, f"failed: {type(error).__name__}: {error}"))


def _client_and_bucket() -> tuple[Any, str]:
    import boto3

    from channelflow.settings import settings_from_env

    settings = settings_from_env()
    storage = dict(settings.storage)
    client = boto3.client(
        "s3",
        endpoint_url=storage.get("s3.endpoint"),
        aws_access_key_id=storage.get("s3.access-key-id"),
        aws_secret_access_key=storage.get("s3.secret-access-key"),
        region_name=storage.get("s3.region", "us-east-1"),
    )
    return client, settings.warehouse.removeprefix("s3://").split("/", 1)[0]


def main(
    argv: Sequence[str] | None = None, *, client: Any = None, bucket: str | None = None
) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--venue", action="append", choices=VENUES, dest="venues", default=None)
    parser.add_argument("--apply", action="store_true", help="move objects; without it, a dry-run")
    arguments = parser.parse_args(argv)

    if client is None or bucket is None:
        client, bucket = _client_and_bucket()
    report = rekey(client, bucket, venues=tuple(arguments.venues or VENUES), apply=arguments.apply)
    print(report.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
