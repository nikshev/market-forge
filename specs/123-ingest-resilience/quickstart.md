# Quickstart: proving the ingest is fixed where it was broken

Two levels again: the suite, which needs nothing, and the running stack. The suite
proves the wiring and the behaviour under a fake connector; **only the live venue can
prove that OKX delivers**, and that check is by hand and recorded with its date.

## Prerequisites

- `make install`
- For the stack sections: `make up` and `docker compose up -d --build`, with `.env` as
  the repository leaves it.

## 1. The suite

```sh
make test-fast
```

The tests that matter, by what each would have caught on 2026-10-02:

| test | would have caught |
|---|---|
| `build_daemon` → OKX connector's `_url` and `_subscribe_msg` | the 404 URL; the `trades.` prefix in `instId` |
| fake connector, reader dies **without** a close frame, `announces_close=True` | Binance and OKX never reconnecting |
| fake clock advanced 24 h on Binance's policy | the lifetime moved into `idle_timeout_ns` |
| fake clock, 1,000 ticks of silence, count the log lines | the 5 Hz warning |
| every `VenuePolicy` in `channelflow.connectors`, grouped by venue | seven definitions in two files |
| `build_daemon` with `s3://…/raw/cex`, archive a frame, read the key | `binance/raw/cex/binance/…` |
| two symbols, one venue, one minute, read both objects back | three processes, one key |
| `FakeS3` interrupted between copy and delete | removal before verification |
| `caplog` at INFO over a recorded segment | INFO on every trade, frame and step |
| `docker-compose.yml` read as YAML | a service with no log cap |

## 2. Against the live venue (by hand)

Run the OKX daemon and watch for a trade:

```sh
docker compose up -d --build ingest-okx
docker compose logs --since 2m ingest-okx | head -20
```

Expected: a "connected" line, **no** `silent connection` and no `rejected`. After fifteen
minutes (one commit) `GET /api/v1/bars?venue=okx&symbol=BTC-USDT-SWAP&timeframe_ns=60000000000`
returns bars. Before this change that request has never returned a row.

**Prove the reconnect with the socket, not the code.** Cut a daemon's network and
restore it:

```sh
docker network disconnect channelflow_default channelflow-ingest-bybit-1
sleep 90
docker network connect channelflow_default channelflow-ingest-bybit-1
docker compose logs --since 3m ingest-bybit | grep -E "down|recover|reconnect"
```

Expected: one WARNING naming the silence, then attempts at 1, 2, 4… seconds while the
network is gone, then one INFO on recovery, with the attempts it took. Not five lines a
second. A plain `docker network connect` does not restore the container's service-name
alias; nothing here resolves `ingest-bybit` by name, but finish with
`docker compose up -d --force-recreate ingest-bybit` so compose and Docker agree again.

## 3. The archive

One hour after the change, count objects per symbol:

```sh
docker compose exec -T api python -c "
import os, time, boto3
from collections import Counter
c = boto3.client('s3', endpoint_url=os.environ['CHANNELFLOW_S3_ENDPOINT'],
  aws_access_key_id=os.environ['CHANNELFLOW_S3_ACCESS_KEY_ID'],
  aws_secret_access_key=os.environ['CHANNELFLOW_S3_SECRET_ACCESS_KEY'], region_name='us-east-1')
n = Counter()
for p in c.get_paginator('list_objects_v2').paginate(Bucket='channelflow-dev', Prefix='raw/cex/binance/'):
    for o in p.get('Contents', []):
        k = o['Key'].split('/')
        # raw/cex/<venue>/<symbol>/YYYY/MM/DD/HHMM.jsonl.gz is 8 parts; the old layout is 7
        if len(k) == 8 and o['LastModified'].timestamp() > time.time() - 3600:
            n[k[3]] += 1
print(dict(n))
"
```

Expected: about 60 each for `BTCUSDT`, `ETHUSDT` and `SOLUSDT` — **180**, not 60. And
nothing under a bare `binance/`, `bybit/` or `okx/` at the bucket root that was written
after the change.

## 4. The migration

Always a dry-run first. It changes nothing:

```sh
docker compose exec -T api python -m channelflow.pipeline.archive_rekey
```

Expected: a report with, per `(venue, symbol)`, the objects that would move and the
minutes present against expected. **Read the refusals.** An object with several symbols
is refused and left, and the report says how many; if that number is not zero something
other than the overwrite produced it.

Then, once the numbers are understood:

```sh
docker compose exec -T api python -m channelflow.pipeline.archive_rekey --apply
docker compose exec -T api python -m channelflow.pipeline.archive_rekey          # second run
```

The second run must report nothing to move. Record both reports in the implement
outcome note: the counts are the answer to FR-014.

## 5. The log

Same measurement as the baseline, 60-second windows:

```sh
for s in ingest-binance ingest-binance-eth ingest-binance-sol ingest-bybit ingest-okx; do
  printf '%-20s %s B/min\n' $s "$(docker compose logs --no-log-prefix --since 60s $s 2>&1 | wc -c)"
done
```

Expected: on the order of 100 bytes a minute each. The baseline is 57,152 to 576,722.

```sh
docker inspect channelflow-ingest-bybit-1 --format '{{json .HostConfig.LogConfig}}'
```

Expected `max-size` and `max-file` present on **every** service, not only these.
Capping takes effect when a container is recreated, not when the file changes:
`docker compose up -d`.
