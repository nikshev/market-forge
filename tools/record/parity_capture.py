"""One-shot recorder for PRD §35.5's live segment: frames in, bars out.

# @trace: REQ-NRT-PARITY

§35.5 asks for a 30–60 minute live segment, replayed offline, with parity
asserted. This captures both halves of that comparison from a running
deployment:

* the **frames** the socket delivered, exactly as [[REQ-WP-066]]'s archive wrote
  them -- one gzip object per minute, copied byte for byte rather than decoded
  and re-serialised. A fixture that had been through a decoder would prove that
  the decoder agrees with itself.
* the **bars** the live run produced from them, read out of the canonical plane.

The two are what makes the test worth having. A replay that reproduces the bars
has reproduced them across the archive, the decoder and every boundary between
the socket and the feature -- which is what a second in-process call of the same
function cannot do.

**Boundary minutes are excluded here, not tolerated later.** A bar spanning the
segment's edge saw trades the segment does not hold, so it is a different bar
and no tolerance should accept it. The window recorded in the manifest is the
half-open interval of minutes wholly inside the capture.

Run deliberately, never in CI, against a stack that has been ingesting:

    .venv/bin/python -m tools.record.parity_capture --minutes 45
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "parity"

MINUTE_NS = 60_000_000_000

#: §35.5 says 30-60 minutes. Below thirty is not the segment the section asks
#: for; above sixty is a fixture nobody wants in a repository.
MINIMUM_MINUTES = 30
MAXIMUM_MINUTES = 60


def _settings() -> Any:
    from channelflow.settings import settings_from_env

    defaults = {
        "CHANNELFLOW_CATALOG_URI": (
            "postgresql+psycopg://channelflow:channelflow_dev_only@127.0.0.1:5432/channelflow"
        ),
        "CHANNELFLOW_WAREHOUSE": "s3://channelflow-dev/warehouse",
        "CHANNELFLOW_S3_ENDPOINT": "http://127.0.0.1:9000",
        "CHANNELFLOW_S3_ACCESS_KEY_ID": "channelflow",
        "CHANNELFLOW_S3_SECRET_ACCESS_KEY": "channelflow_dev_only",
        "CHANNELFLOW_S3_REGION": "us-east-1",
    }
    for name, value in defaults.items():
        os.environ.setdefault(name, value)
    return settings_from_env()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=45)
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--venue", default="binance")
    args = parser.parse_args()
    if not MINIMUM_MINUTES <= args.minutes <= MAXIMUM_MINUTES:
        raise SystemExit(
            f"§35.5 asks for {MINIMUM_MINUTES}-{MAXIMUM_MINUTES} minutes, not {args.minutes}"
        )

    import boto3  # noqa: PLC0415 -- only this tool needs it

    settings = _settings()
    storage = dict(settings.storage)
    s3 = boto3.client(
        "s3",
        endpoint_url=storage["s3.endpoint"],
        aws_access_key_id=storage["s3.access-key-id"],
        aws_secret_access_key=storage["s3.secret-access-key"],
        region_name=storage.get("s3.region", "us-east-1"),
    )
    bucket = settings.warehouse.removeprefix("s3://").split("/", 1)[0]

    prefix = f"raw/cex/{args.venue}/"
    keys: list[str] = []
    token: str | None = None
    while True:
        more = {"ContinuationToken": token} if token else {}
        page = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, **more)
        keys.extend(item["Key"] for item in page.get("Contents", ()))
        token = page.get("NextContinuationToken")
        if not token:
            break
    keys.sort()
    if len(keys) < args.minutes + 2:
        raise SystemExit(f"only {len(keys)} archived minutes; need {args.minutes + 2}")

    # One minute of margin at each end: the first and last are where a bar can
    # span the boundary, and a fixture that included them would be asking the
    # replay to reproduce trades it was never given.
    chosen = keys[-(args.minutes + 1) : -1]
    print(f"{len(keys)} archived minutes; taking {len(chosen)}: {chosen[0]} .. {chosen[-1]}")

    FIXTURES.mkdir(parents=True, exist_ok=True)
    frames_dir = FIXTURES / "frames"
    frames_dir.mkdir(exist_ok=True)
    total = 0
    for key in chosen:
        payload = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        (frames_dir / Path(key).name).write_bytes(payload)
        total += len(payload)
    print(f"wrote {len(chosen)} objects, {total / 1024:.0f} KiB")

    from channelflow.lakehouse import catalog as open_catalog  # noqa: PLC0415

    store = open_catalog(uri=settings.catalog_uri, warehouse=settings.warehouse, **storage)
    rows = store.load_table("channelflow.bars").scan().to_arrow().to_pylist()

    first_ns = _minute_ns(chosen[0])
    last_ns = _minute_ns(chosen[-1]) + MINUTE_NS
    inside = [
        row
        for row in rows
        if row["symbol"] == args.symbol
        and row["venue"] == args.venue
        and first_ns <= int(row["open_time_ns"])
        and int(row["close_time_ns"]) <= last_ns
    ]
    inside.sort(key=lambda row: int(row["open_time_ns"]))
    if not inside:
        raise SystemExit("no live bars inside the window; the plane holds none for it")

    (FIXTURES / "bars.jsonl").write_text(
        "".join(json.dumps(_plain(row), sort_keys=True) + "\n" for row in inside)
    )
    (FIXTURES / "manifest.json").write_text(
        json.dumps(
            {
                "venue": args.venue,
                "symbol": args.symbol,
                "minutes": len(chosen),
                "window_start_ns": first_ns,
                "window_end_ns": last_ns,
                "frames_bytes": total,
                "live_bars": len(inside),
                "first_object": Path(chosen[0]).name,
                "last_object": Path(chosen[-1]).name,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(f"{len(inside)} live bars inside the window; manifest written")


def _minute_ns(key: str) -> int:
    """The archive's key back into the instant it names."""
    from datetime import UTC, datetime  # noqa: PLC0415

    path = Path(key)
    stem = path.name.removesuffix(".jsonl.gz")
    day, month, year = path.parent.name, path.parent.parent.name, path.parent.parent.parent.name
    at = datetime(int(year), int(month), int(day), int(stem[:2]), int(stem[2:]), tzinfo=UTC)
    return int(at.timestamp()) * 1_000_000_000


def _plain(row: dict[str, Any]) -> dict[str, Any]:
    """Arrow gives Decimals and datetimes; a fixture holds strings and ints."""
    return {
        key: (value if isinstance(value, int | str) else str(value)) for key, value in row.items()
    }


if __name__ == "__main__":
    main()
