# Contract: the raw archive and `src/channelflow/pipeline/archive_rekey.py`

## Key layout

```text
raw/cex/<venue>/<symbol>/<YYYY>/<MM>/<DD>/<HHMM>.jsonl.gz
```

One object per venue, symbol and **receipt** minute (UTC). Each line is
`{"received_at_ns": …, "frame": "…"}`, as today; `read_frames` is unchanged.

## `FrameArchive`

```python
FrameArchive(store: ObjectStore, venue: str, symbol: str, prefix: str = "raw/cex")
FrameArchive.key_for(minute_start_ns: int) -> str
```

- `ValueError` if `symbol` is empty or contains `/`, or `venue` is.
- `key_for` returns the layout above and nothing else.
- `flush()` logs **only when it writes** (DEBUG otherwise). Today it logs, at INFO, on
  every step with an empty buffer.

**Guarantee**: two archives of one venue with different symbols, flushed in the same
minute against one store, leave **two** objects; reading each back with `read_frames`
yields only that symbol's frames. Tested by reading the frames, not by comparing keys —
the earlier mistake was a correct-looking string.

## `build_daemon` and the archive

`build_daemon` passes `prefix` as the path component of `CHANNELFLOW_ARCHIVE_URI`
(`raw/cex` for `s3://bucket/raw/cex`), the registry's venue, and the configured symbol.
**It does not prefix the venue.** Tested through `build_daemon`, with the deployment's
own URI, by archiving a frame and reading the key back:

- the venue occurs **once** in the key;
- the key starts with `raw/cex/`;
- the symbol is present, in the configured spelling.

## `src/channelflow/pipeline/archive_rekey.py`

```text
python -m channelflow.pipeline.archive_rekey [--bucket B] [--venue V]... [--apply]
```

**Dry-run unless `--apply`.** Prints the report; changes nothing. Credentials and the
endpoint come from the same environment `settings_from_env` reads.

**Old layouts it recognises**

| layout | pattern | count at last measure |
|---|---|---|
| A, no symbol | `raw/cex/<venue>/<YYYY>/<MM>/<DD>/<HHMM>.jsonl.gz` | 12,850 (binance) |
| B, misplaced | `<venue>/raw/cex/<venue>/<YYYY>/<MM>/<DD>/<HHMM>.jsonl.gz` | 11,975 (binance 3,015, bybit 8,960) |

**Attribution.** The symbol comes from the object's own frames: Binance `stream`
(`btcusdt@aggTrade` → `BTCUSDT`), Bybit `topic` (`publicTrade.BTCUSDT`), OKX
`arg.instId`. The symbol is written in the configured spelling — upper case for Binance
and Bybit — never as the lower-case stream label. A frame carrying no symbol (a pong, an
acknowledgement, an OKX `event`) is ignored for attribution.

**Per object**

1. Parse the key into venue and minute. A key matching neither layout → `Refuse`.
2. Read and decode the frames. Zero attributable → `Refuse("no attributable frame")`.
   More than one distinct symbol → `Refuse("several symbols: [...]")`.
3. Destination absent → `Move`. Destination present and identical (size and ETag) →
   `AlreadyThere`. Present and different → `Refuse("destination holds different bytes")`.
4. `Move`: `copy_object`; `head_object` on source and destination; **proceed only if size
   and ETag are equal**; then `delete_object` on the source.

**Guarantees**

1. **Never removes before verifying.** An interrupted run leaves a duplicate, not a gap.
2. **Idempotent.** A second run reports `AlreadyThere` or nothing and converges.
3. **Never moves an object it cannot attribute to exactly one symbol.**
4. **Reports the extent.** For each `(venue, symbol)`, distinct minutes present and minutes
   expected between the first and last object, so the overwritten minutes are a number.
   It is a lower bound: it cannot see before the first or after the last object.

## `tools/record/parity_capture.py`

Gains `--symbol` (required) and lists `raw/cex/<venue>/<symbol>/`. Without it the
listing would return every symbol's minutes interleaved, and a replay would be built
from frames of several instruments.

## Tests, and what they run against

`tests/unit/pipeline/test_archive_rekey.py` uses a hand-written `FakeS3` implementing exactly
`list_objects_v2`, `get_object`, `head_object`, `copy_object`, `delete_object` and
`put_object`, with ETags derived from content. `moto` is not a dependency of this
project. The fake can be made to fail between copy and delete, so "never removes before
verifying" is tested by interrupting it.
