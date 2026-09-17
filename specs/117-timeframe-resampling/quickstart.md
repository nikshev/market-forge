# Quickstart: proving the timeframes are real

Two levels: the suite, which needs nothing, and the running stack, which is the
only place the claim "a chart shows candles" can be checked.

## Prerequisites

- `make install`
- For the stack section: `make up` and `docker compose up -d`, with the ingest
  daemon writing one-minute bars.

## 1. The suite

```sh
make test-fast
```

Everything in this feature is unit-testable: the resampler is pure functions
over `Bar` values, so no catalog, no object store and no network. It runs in the
fast gate, which means a commit that breaks the arithmetic fails before it
lands.

The tests that matter most, by what they would catch:

| test | catches |
|---|---|
| a window whose minutes differ in every field | a fold that reads only the ends |
| a window containing a Thursday | epoch-aligned weeks |
| a window missing one minute of 240 | a bar assembled from what was there |
| a second pass over one source | duplicate rows |
| `vwap` over minutes of unequal volume | averaging the averages |
| `4h` configured where no fixture used it | a hard-coded timeframe set |

## 2. Against the running stack

**Before.** One series, and the chart's request returns nothing:

```sh
curl -s "localhost:8000/api/v1/bars?venue=binance&symbol=BTCUSDT&timeframe_ns=60000000000&limit=2"
curl -s "localhost:8000/api/v1/bars?venue=binance&symbol=BTCUSDT&timeframe_ns=900000000000&limit=2"
```

Measured 2026-09-17: the first returns bars, the second returns `{"bars":[]}`.

**Run one pass.**

```sh
docker compose run --rm resample python -m channelflow.pipeline.resample_main --once
```

Expect one report line per `(venue, symbol, timeframe)`, and — on a deployment
whose ingest started mid-window — at least one refusal naming the first,
partial window. **A run with no refusals at all on a freshly started stack is
itself suspicious**: the minute the daemon started in is almost never whole.

**After.**

```sh
curl -s "localhost:8000/api/v1/bars?venue=binance&symbol=BTCUSDT&timeframe_ns=900000000000&limit=3"
```

Expect final bars whose `open_time_ns` values are multiples of 900e9.

**Prove idempotence with the tool itself**, not by reasoning about it:

```sh
docker compose run --rm resample python -m channelflow.pipeline.resample_main --once
```

The second pass must report `written=0` with a non-zero `skipped`. If `written`
is non-zero, the table now holds duplicates — `read_bars` will return both, and
nothing below the producer will complain.

**Count rows directly** when the report and the table need to be compared:

```sh
docker compose exec -T api python -c "
import os
from channelflow.settings import settings_from_env
from channelflow.lakehouse import catalog as open_catalog
from channelflow.tables import bars
s = settings_from_env(os.environ)
t = bars.table_for(open_catalog(uri=s.catalog_uri, warehouse=s.warehouse, **dict(s.storage)))
rows = t.read().to_pylist()
from collections import Counter
print(Counter(r['timeframe_ns'] for r in rows))
print('duplicate keys:', len(rows) - len({(r['venue'], r['symbol'], r['timeframe_ns'], r['open_time_ns']) for r in rows}))
"
```

`duplicate keys: 0` is the assertion. This is the same read the measurement in
`plan.md` used — 89 rows in 132ms at the time it was written.

## 3. The chart

Open `/chart/binance/BTCUSDT?tf=15m`.

**This will still show nothing after this feature**, and that is expected: the
chart builds its request from a constant, not from `tf`. That defect is
[[REQ-WP-074]], the next requirement in the chain. Named here so that a reader
running this quickstart does not conclude the resampler failed.

What can be checked today is the API, which is what section 2 does.
