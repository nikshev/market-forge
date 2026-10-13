# Running ChannelFlow

<!-- @trace: REQ-WP-056 -->
<!-- @trace: REQ-WP-072 -->

This describes what actually runs. It is checked against the repository by
`tests/unit/docs/test_deployment_doc.py`: every command named here is a real
`make` target, every service is in `docker-compose.yml`, and every variable is in
`.env.example`. A command renamed without this file changing fails that test
rather than leaving prose that is confident, plausible and wrong.

## What the stack is

Thirteen services, started together:

| service | what it is for |
|---|---|
| `postgres` | transactional metadata and the Iceberg catalog |
| `minio` | the S3-compatible object store the canonical plane writes to |
| `redpanda` | the Kafka-protocol event backbone |
| `prometheus` | scrapes the API's exposition |
| `grafana` | renders the dashboard generated from the code |
| `api` | the read API of PRD §28, built from this repository ([[REQ-WP-064]]) |
| `web` | the chart application, static files behind nginx, which proxies `/api` to `api` |
| `ingest-binance` | the live connector: one symbol, socket to bars ([[REQ-WP-066]]) |
| `ingest-binance-eth` | the same, for ETHUSDT |
| `ingest-binance-sol` | the same, for SOLUSDT |
| `ingest-okx-spot-btc`, `-eth`, `-sol` | OKX **spot** `BTC-USDT`, `ETH-USDT`, `SOL-USDT`: the second spot venue, so the Binance spot series have a venue basis ([[REQ-WP-098]]) |
| `resample` | builds every configured timeframe from the one-minute series, on a loop ([[REQ-WP-073]]) |
| `maintenance` | prunes metadata, compacts and optionally expires, on a loop ([[REQ-WP-070]]) |
| `worker` | fits channels, signals and extrema over the stored bars, on a loop ([[REQ-WP-077]]) |
| `context-binance`, `context-bybit`, `context-okx` | the context collectors: one per venue, polling its public derivatives endpoints (open interest, funding, mark and index) into `derivatives_state`; no key, no feature computed ([[REQ-WP-093]]) |
| `notary` | **only when asked for** (`docker compose up -d notary`): commits a Merkle root of the records the worker registered to the SignalNotary contract on Monad testnet, and is the one service given the signing keystore ([[REQ-INFRA-007]]) |
| `cloudflared` | **only with `--profile telegram`**: an outbound tunnel that gives the web service an HTTPS address for the Telegram Mini App ([[REQ-WP-080]]) |

All eight application services build from this repository ([[REQ-WP-064]],
[[REQ-WP-066]], [[REQ-WP-070]], [[REQ-WP-073]], [[REQ-WP-077]]) rather than pulling a tag naming
a build nobody in this checkout can reproduce. `worker` is the §6.2 service
that had no container until [[REQ-WP-077]] gave `record_replay` a process to
run in: it reads the bars each configured timeframe holds and writes the
channel snapshots, signals and extrema.

**Three ingest services, not one taking three symbols.** §5.1's Phase 1 universe
is BTCUSDT, ETHUSDT and SOLUSDT, and `ingest_main` refuses a configuration
naming more than one symbol: a daemon multiplexing several would share one
socket's failure across all of them, so one stalled symbol would stop the others
without saying so. The first keeps §6.2's bare spelling `ingest-binance`.

**Higher timeframes are produced by `resample`, not by more sockets.**
`CHANNELFLOW_TIMEFRAMES` names what the pass builds from the stored one-minute
series — `5m,15m,30m,1h,4h,1d,1w` by default. It is a service of its own rather
than a corner of `maintenance`, because that one removes and a producer hidden
inside it would be found by whoever read the compose file last. Every pass is
idempotent: it reads the open times already written and produces only what is
missing, so the loop interval is a freshness knob and never a correctness one.
`1M` is refused by the token parser rather than approximated as 30 days: a
calendar month has no fixed nanosecond duration, and a monthly boundary that
drifts against the calendar is wrong in a way a reader of a chart cannot see.

**Channels have a producer now.** `worker` reads the bars each configured
timeframe holds and calls `record_replay`, which writes the channel snapshots,
signals, confirmed extrema and extremum candidates. A pass over unchanged bars
writes nothing — proven by counting rows before and after, not by trusting the
watermarks — and one timeframe failing does not end the pass. Measured
2026-09-17: 133 bars, zero channel snapshots; that reading is what [[REQ-WP-077]]
closed.

*(This paragraph said the opposite until 2026-09-14 — that the API and web app
were not containerised. `tests/unit/docs/test_deployment_doc.py` checks that
every **name** in this document is real, and it passed throughout. A document
checked for names can still be confidently wrong about everything else, which is
why the exposure table below is checked service by service.)*

## Where the data lives

Every stateful service writes into `CHANNELFLOW_DATA_DIR` — `./data` in a
checkout, and on a server whatever disk is mounted for it. Not a Docker named
volume: the data has to be copyable, movable and backed up with ordinary tools.

**Prepare the directory before the first start:**

```sh
make data-dirs
```

It creates one directory per service and gives each to the user that service
runs as. That step is not a formality. A named volume is initialised by Docker,
which copies the image's ownership onto it; a bind mount keeps whatever the host
directory already has, and the five images run as five different users —
`postgres` and `minio` as root, `redpanda` as 101, `prometheus` as 65534,
`grafana` as 472. A directory one of them cannot write is a container that fails
to start, or one that starts and never persists.

**It cannot be tested by hand on a Mac.** Docker Desktop maps bind-mount access
onto the host user, so every service reports the directory writable whatever
owns it. `make data-dirs` checks each directory **as the user the service is**,
which is the only check that means anything on the machine this matters on.

To back the stack up, stop it and copy the directory. To move it to another
machine, copy the directory.

## Keeping it fast

The plane is append-only, so every commit leaves a data file. A symbol at
one-minute bars leaves about 96 a day, and a read costs one round trip to the
object store per file.

```sh
make compact
```

Rewrites each table's live rows into one file, preserving the order a read
guarantees. Measured on a table of 717 files holding 721 rows: 7.2 seconds once,
and the read that followed took **45ms against 6478ms** ([[REQ-WP-068]]).

The `maintenance` service runs this on a loop, every
`CHANNELFLOW_MAINTENANCE_INTERVAL`. Run `make compact` by hand when you want it
sooner.

**Expiry is opt-in.** `CHANNELFLOW_KEEP_DAYS` empty means compact and keep
everything: expiring snapshots is the only operation in this system that
destroys ([[ADR-062]]), and compacting without it is safe and costs storage.
Set it to a number of days when you have decided what this deployment may
forget.

Measured before any of this existed: a table holding **2.6 MB of bar data and
304.9 MB of metadata**, with 933 data files where its current snapshot used
one.

## On a remote host, from `git clone`

Written for a fresh Linux host. Every command is one you can paste; the two
that need `sudo` say so.

### 1. What the host needs

```sh
docker --version          # 24+ ; the compose plugin comes with it
docker compose version
git --version
curl -LsSf https://astral.sh/uv/install.sh | sh    # uv, for `make data-dirs`
```

Only `make data-dirs` needs Python on the host — it reads each image's uid and
chowns the directories to match. Everything else runs in containers.

### 2. Clone and configure

```sh
git clone git@github.com:nikshev/market-forge.git
cd market-forge
cp .env.example .env
```

**Edit `.env` before going further.** Three things matter, and the stack will
stop and tell you about the third:

| variable | change it to |
|---|---|
| `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD` | anything that is not `channelflow_dev_only` |
| `GRAFANA_ADMIN_PASSWORD` | a password. Compose refuses to start without one — blank makes Grafana fall back to `admin` |
| `CHANNELFLOW_DATA_DIR` | the mounted disk, e.g. `/srv/channelflow/data`. Everything stateful lives there |

Leave `CHANNELFLOW_BIND_ADDRESS=127.0.0.1` alone unless you have decided a
service should be reachable from outside the host. See "What is exposed".

### 3. Prepare the data directory

```sh
make install              # a virtualenv; needed only for the next command
sudo -E make data-dirs    # creates each directory and gives it to its service
```

`sudo` because it chowns. The five images run as five different users —
`postgres` and `minio` as root, `redpanda` as 101, `prometheus` as 65534,
`grafana` as 472 — and a bind mount keeps whatever the host directory already
has. A directory one of them cannot write is a container that starts and never
persists, or one that does not start at all.

It verifies each directory **as the user the service is**, which is the only
check that means anything: a check run as the operator would pass everywhere.

### 4. Start it

```sh
make up                              # postgres and minio, waiting until healthy
docker compose up -d --build         # everything else, built from this checkout
docker compose ps                    # all healthy?
```

`make up` deliberately starts only the two stateful services the test suite
needs. The second command brings up the API, the web app, the three ingest
daemons, the resampler, maintenance, Prometheus and Grafana, building the seven
application images from this checkout rather than pulling a tag nobody here can
reproduce.

First build takes a few minutes. After it, the ingest daemon connects to Binance
and the first bar appears about a minute later.

### 5. Reach it

Nothing listens on an external interface. Open an SSH tunnel from your own
machine:

```sh
ssh -N -L 8080:127.0.0.1:8080 -L 3000:127.0.0.1:3000 user@your-host
```

| | |
|---|---|
| `http://localhost:8080` | the markets overview (also `/markets`) |
| `http://localhost:8080/chart/binance/BTCUSDT?tf=15m` | a chart at a timeframe; PRD §27.1's deep link |
| `http://localhost:3000` | Grafana |

Every other path serves the same bundle and shows where a chart can be opened
(`nginx.conf` falls back to `index.html`), so a mistyped URL says so rather
than 404ing. The overview is one row per market from `GET /api/v1/markets`,
in §43's rank order ([[REQ-WP-075]]), with unscored markets shown as
unscored rather than as zero.

Add `-L 9001:127.0.0.1:9001` for the MinIO console if you want to see the
objects.

### 6. Check that it is actually working

```sh
docker compose logs --tail 20 ingest-binance     # frames arriving
curl -s localhost:8000/readyz                    # {"ready": true, ...}
docker compose exec -T minio sh -c 'ls /data/*/raw/cex/binance/BTCUSDT/*/*/*/ | tail -3'
```

The third is the raw archive — one gzip object per minute **per symbol**. If it is
growing, the socket is connected and the frames are being kept. See "The raw archive".

### Everyday commands

```sh
docker compose logs -f ingest-binance    # follow the connector
docker compose restart api               # after a config change
git pull && docker compose up -d --build # after an update
make down                                # stop, keeping the data
```

**To back it up:** stop the stack and copy `CHANNELFLOW_DATA_DIR`. To move it to
another machine, copy that directory. That is the whole procedure, and it is why
nothing here uses a Docker named volume.

**`make reset` deletes the data.** It is the only destructive command in this
file.

### If something does not start

| symptom | cause |
|---|---|
| `required variable GRAFANA_ADMIN_PASSWORD is missing a value` | `.env` predates that variable. Add it — this is the intended refusal |
| a container restarts forever | its data directory is not writable by its uid. Re-run `sudo -E make data-dirs` |
| `/readyz` answers 503 | the API started and cannot read its warehouse. Check `minio` is healthy and the bucket exists |
| the chart is empty | give it a minute. The first bar needs a minute of trades |

## Starting it

```
make install      # a virtualenv and dependencies
make up           # the containers, waiting until each is healthy
make test         # the full suite, which needs the stack up
make down         # stop, keeping the data
make reset        # stop and delete the volumes -- destructive
```

`make up` waits for health rather than sleeping, so a green return means the
services will answer, not that they have started.

## What must be supplied

Copy `.env.example` to `.env`. It carries names with empty values and never a
secret; `.env` is not committed and never should be.

| variable | what it is |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` | the database |
| `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_PORT`, `MINIO_CONSOLE_PORT`, `MINIO_BUCKET` | the object store |
| `REDPANDA_PORT` | the event backbone |
| `PROMETHEUS_PORT`, `GRAFANA_PORT` | observability |
| `API_PORT`, `WEB_PORT` | where the application services are published |
| `CHANNELFLOW_DATA_DIR` | the directory every stateful service writes into ([[REQ-WP-065]]) |
| `CHANNELFLOW_DEX_RPC_URL`, `CONTEXT_HYPEREVM_PORT` | the HyperEVM JSON-RPC node the DEX collector reads (empty: the public one) and the port it serves `/healthz` on |
| `CHANNELFLOW_KAFKA_BOOTSTRAP` | where the ingest daemons publish the bars they are building and the API reads them back, for the chart's live feed ([[REQ-WP-102]]); inside the compose network `redpanda:29092`, empty turns the feed off and the chart reloads on a timer |
| `CHANNELFLOW_BIND_ADDRESS` | what every published port binds to; `127.0.0.1` by default ([[REQ-WP-072]]) |
| `CHANNELFLOW_CORS_ORIGINS`, `CHANNELFLOW_RATE_LIMIT`, `CHANNELFLOW_RATE_WINDOW_SECONDS` | what the read API allows and refuses |
| `GRAFANA_ADMIN_PASSWORD`, `GRAFANA_ANONYMOUS` | Grafana's credential; anonymous access is off unless enabled |
| `CHANNELFLOW_INGEST_SYMBOLS`, `CHANNELFLOW_INGEST_SYMBOLS_ETH`, `CHANNELFLOW_INGEST_SYMBOLS_SOL`, `CHANNELFLOW_INGEST_SYMBOLS_BYBIT`, `CHANNELFLOW_INGEST_SYMBOLS_BYBIT_HYPE`, `CHANNELFLOW_INGEST_SYMBOLS_OKX_HYPE`, `CHANNELFLOW_INGEST_SYMBOLS_OKX`, `CHANNELFLOW_INGEST_SYMBOLS_OKX_SPOT_BTC`, `CHANNELFLOW_INGEST_SYMBOLS_OKX_SPOT_ETH`, `CHANNELFLOW_INGEST_SYMBOLS_OKX_SPOT_SOL`, `CHANNELFLOW_INGEST_TIMEFRAME_NS`, `CHANNELFLOW_INGEST_VENUE`, `CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS` | what each ingest daemon reads, which venue it connects to, at what bar size, and how long silence is tolerated before it reconnects (empty: the venue's own 60 s) — one symbol and venue per process |
| `CHANNELFLOW_LOG_LEVEL`, `CHANNELFLOW_LOG_MAX_SIZE`, `CHANNELFLOW_LOG_MAX_FILE` | how loud the ingest daemons are (empty is INFO), and the cap on every service's container log — 20 MB × 3 files by default |
| `CHANNELFLOW_TIMEFRAMES`, `CHANNELFLOW_RESAMPLE_INTERVAL` | which timeframes the resampler builds from the one-minute series, and how often it runs ([[REQ-WP-073]]); `1M` is refused. The read API reads the same variable and reports the set at `GET /api/v1/timeframes` ([[REQ-WP-074]]) — one value for both processes, so what a chart offers cannot disagree with what exists |
| `CHANNELFLOW_MAINTENANCE_INTERVAL`, `CHANNELFLOW_KEEP_DAYS` | how often maintenance runs, and what it may expire |
| `CHANNELFLOW_CHANNEL_INTERVAL` | how often the channel worker re-fits over the stored bars ([[REQ-WP-077]]) |
| `CHANNELFLOW_CONSENSUS_INTERVAL`, `CHANNELFLOW_CONSENSUS_STALENESS_NS` | how often the cross-venue consensus pass runs (5m, the same grammar as `CHANNELFLOW_CHANNEL_INTERVAL`) and how old a quote may be at a bar's close and still count toward the median, in nanoseconds (60000000000 is 60 s; a staler one is excluded with its reason) ([[REQ-WP-091]]) |
| `CHANNELFLOW_GAP_THRESHOLD` | how large a hole in the bar series the extremum detector and the channel fit treat as contiguous before they restart at it — 1 (the default) bridges a single missing bar and restarts on two or more, 0 restarts on any gap, a larger value bridges up to that many ([[REQ-WP-087]]) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | alert delivery, empty unless alerting is wanted |
| `CHANNELFLOW_CHART_BASE_URL` | where an alert's chart link points |

The credentials in `.env.example` are development defaults and say so in their
values. PRD §34 requires the Telegram token to come from a secret manager in
anything that is not a laptop, and nothing in this repository reads it from the
environment on its own: the transport and its credentials are supplied by the
caller ([[ADR-018]]).

## Opening it inside Telegram

[[REQ-WP-080]]. The overview and the chart open as a Telegram Mini App, from a bot, as `lexa-reader`
does. Nothing the pages show changes; the stack gains an optional tunnel and the API gains an optional
gate.

**What the gate is.** Access control, not secrecy. The data is public market data. The gate stops the
public address from being a free read API and makes "opens inside Telegram" mean something. Telegram
signs a launch; the API verifies it on every request, stores nothing, and keeps no user. A captured
launch can be replayed until it ages out, which is `CHANNELFLOW_TELEGRAM_MAX_AGE_SECONDS` (a day unless
set). `CHANNELFLOW_TELEGRAM_AUTH` is `off` unless it is `required`; `required` without
`TELEGRAM_BOT_TOKEN` stops the service rather than serve open, and any other spelling is refused.

**What the public address reaches.** The web service's nginx proxies `/api/` and nothing else, and the
API serves its data under `/api/v1/`. `/readyz` and `/metrics` are outside that prefix and are not
reachable through the tunnel; `tests/unit/deploy/test_public_surface.py` keeps it so. The websocket is
closed to an unsigned caller when authentication is required; the page does not use it.

**To set it up.**

1. Create the bot with BotFather (`/newbot`). Its token goes in `.env` as `TELEGRAM_BOT_TOKEN`, the same
   variable the alert sender reads.
2. Create a Cloudflare Tunnel (Zero Trust, Networks, Tunnels, Cloudflared). Copy its token into `.env` as
   `CHANNELFLOW_TUNNEL_TOKEN`. Add a public hostname whose service is HTTP at `web:8080`.
3. Set `CHANNELFLOW_TELEGRAM_AUTH=required` in `.env`. Leave `CHANNELFLOW_TUNNEL_PROTOCOL` at `http2`:
   UDP egress to Cloudflare is blocked on this host.
4. Start it: `docker compose --profile telegram up -d --build`.
5. In BotFather create the Mini App (`/newapp`) with the public hostname as its URL.
6. Check: `curl https://<hostname>/api/v1/timeframes` answers 401 with a reason, not data. Then open the
   bot in Telegram on a phone.

**Two forms of a link.** An alert's button may carry the full deep link as before. A link of the form
`t.me/<bot>/<app>?startapp=<value>` carries the same chart state as a `start_param`: the base64url of
the deep link's path and query, at most 512 characters. A value that cannot be read opens the overview.

**Developing without Telegram.** From `apps/web`, `npm run dev:init` writes a freshly signed launch to
`.env.development.local`, so the authentication can be exercised in a plain browser. It is never written
to `.env.local`: Vite reads that in a production build too, and `docker build` copies whatever is in the
directory. The application reads it only in development, `apps/web/.dockerignore` keeps it out of the
image, and a test builds for production with a marker in it and searches the output.

## What is exposed, and to whom

Every published port binds `CHANNELFLOW_BIND_ADDRESS`, which defaults to
`127.0.0.1` ([[REQ-WP-072]]). With the default, nothing listens on an external
interface: reach the stack over an SSH tunnel.

```sh
ssh -N -L 8080:127.0.0.1:8080 -L 3000:127.0.0.1:3000 user@server
```

| service | published as | reachable by default from |
|---|---|---|
| `postgres` | `POSTGRES_PORT` | the host only |
| `minio` | `MINIO_PORT`, `MINIO_CONSOLE_PORT` | the host only |
| `redpanda` | `REDPANDA_PORT` | the host only |
| `api` | `API_PORT` | the host only |
| `web` | `WEB_PORT` | the host only |
| `prometheus` | `PROMETHEUS_PORT` | the host only |
| `grafana` | `GRAFANA_PORT` | the host only |

`tests/unit/deploy/test_exposure.py` reads `docker-compose.yml` and fails on any
published port that does not bind through that variable. A service meant to be
public is named there, with its reason, where somebody reviewing security will
find it.

**Binding to loopback removes a question rather than answering it.** On Linux,
Docker inserts its rules into the nat table's DOCKER chain, traversed before
the INPUT chain that `ufw` manages by default — so a published port can be
reachable while `ufw` reports it denied. A port that never listens externally
cannot be reached however the firewall is configured.

## What the read API refuses

PRD §34 asks for a rate limited public API with restricted CORS. Both are
configuration:

| variable | default | meaning |
|---|---|---|
| `CHANNELFLOW_RATE_LIMIT` | empty | requests per window; **empty means no limiting at all** |
| `CHANNELFLOW_RATE_WINDOW_SECONDS` | `60` | the window |
| `CHANNELFLOW_CORS_ORIGINS` | empty | comma-separated; empty allows no cross-origin read; `*` is refused at startup |

**What the limiter keys on**: the client address as the application sees it.
Behind a proxy that is the proxy's address — it does not trust a forwarded
header, because trusting one is a decision with its own risks.

**Its scope is one process.** The count lives in memory. With N API processes the
effective limit is N times the configured one. This deployment runs one; the
arithmetic is written here so the day a second appears the cost is visible rather
than discovered.

**Its edge behaviour**: a fixed window admits up to twice the limit across a
boundary — the last requests of one window and the first of the next.

`/readyz` and `/metrics` are never limited. Throttling a readiness probe makes an
orchestrator declare the service unhealthy, which is the outage the limiter
exists to prevent.

## The raw archive

Every frame a venue sends is kept, uninterpreted, one gzip object per venue, symbol and
minute:

```text
raw/cex/<venue>/<symbol>/<YYYY>/<MM>/<DD>/<HHMM>.jsonl.gz
```

The minute is the **receipt** time, in UTC. The symbol is the one configured —
BTCUSDT on Binance and Bybit, `BTC-USDT-SWAP` on OKX. Binance and Bybit symbols must be
upper case, and a lower-case one is refused at start-up: the key and the migration both use
that spelling, and `btcusdt` would put one instrument in two directories.

The symbol is in the key because each symbol is its own process. Until 2026-10-02 it was
not, and three Binance processes wrote one key between them: `store.put` replaces an
object, so the last process to flush a minute won, and every minute held the frames of one
of BTCUSDT, ETHUSDT and SOLUSDT. What was overwritten cannot be recovered. Measured by the
bars the same minutes produced, the archive lacks 62% of BTCUSDT's minutes, 66% of
ETHUSDT's and 57% of SOLUSDT's from 2026-09-17 to the day it was fixed. Bars and channels
are built from the live stream and not read back from the archive, so they are unaffected.

A restart inside a minute still replaces that minute's object with the tail written after
it. That is not fixed.

**Moving what was written under the old keys.** Objects under `raw/cex/<venue>/<date>/…`
and under `<venue>/raw/cex/<venue>/…` are placed under the symbol their own frames name:

```sh
docker compose exec -T ingest-bybit python -m channelflow.pipeline.archive_rekey          # a dry-run
docker compose exec -T ingest-bybit python -m channelflow.pipeline.archive_rekey --apply
```

It is a dry-run unless `--apply` is given. An object is copied, compared with its source by
size and checksum, and only then removed, so an interruption leaves a duplicate and never a
gap, and a second run finishes it. An object holding several symbols, or none, is refused and
left where it is, with the reason printed.

## When a connection ends

A connection that ends is reopened, for every venue and whatever ended it: the stream
reaches the age at which the venue closes it (24 hours on Binance), the connector's reader
thread ends, or nothing arrives for longer than the venue is allowed to be silent
(`CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS`, 60 s unless set).

The log says so once when a connection goes down, with the reason; again at the 2nd, 4th,
8th… failed attempt; and once when frames return, with how many attempts it took. Attempts
back off from one second and stop doubling at a minute. A refusal from the venue is a
WARNING quoting the venue's own words — OKX's `Subscribe failed …`, Bybit's `handler not
found`. Binance sends none that has been observed, so for Binance a refused request is
silence.

## The volume profile's price bins

PRD §14.1 asks for volume by price level from the trades, split into aggressive buying and selling. A stored bar has that split for
the whole bar and no price inside it, so the ingest collects the price bins itself, from the moment it is deployed: **there is no
history**, and none is inferred from bars. A 4 h profile is complete four hours after deployment, a 24 h profile after a day, a 7 d
profile after a week, and the API says how much of its window the data covers.

Each ingest process aggregates its symbol's trades per five-minute block and per price bin (buy, sell and unknown base volume, by the
trade's aggressor side only) and writes them to the `volume_bins` table with the bars. A block whose trade ids show missed trades
(Binance, whose ids are sequential) is dropped and logged, not written.

| Variable | Meaning |
|---|---|
| `CHANNELFLOW_PROFILE_BIN_WIDTHS` | quote units per bin, per symbol: `binance:BTCUSDT=20,okx:BTC-USDT-SWAP=10`. Empty derives each symbol's from its first trade (about two basis points of the price, rounded to 1-2-5, logged at start). The width is written on every row; a profile uses the latest width on record |
| `CHANNELFLOW_PROFILE_BLOCK_SECONDS` | the block length, a whole number of minutes in seconds; empty is 300 |
| `VITE_CHART_REFRESH_MS` | the chart's live refresh interval in milliseconds (REQ-WP-090, Principle X). Default 60000 (60 s). <=0 or unparseable disables the timer |

## Which markets are listed

[[REQ-WP-081]]. The overview (`/markets`, [[REQ-WP-075]]) lists what the markets table holds, and each
ingest service **registers the market it ingests** in that table when it starts, once: its venue, its
symbol and the venue's market type, with no trading rules (nothing reads them, and only Binance has a
normalizer). Starting a service again adds nothing, and a failure to register is one warning naming the
venue and the symbol: ingest goes on, because the bars are the product and the list is not.

The market type is the **feed's**, not the venue's reputation. The Binance service connects to
`stream.binance.com`, Binance's **spot** stream, so it is listed as spot; the Bybit service connects to
Bybit's linear endpoint and OKX is read from its instrument (`BTC-USDT-SWAP` is a perpetual), so those
are perpetuals. PRD §26.1's example alert says "Binance Perp"; this deployment's Binance data is not. A
test ties each type to the endpoint the service really uses, so moving a feed to another market fails
until the type is reconsidered. An OKX instrument that is neither a swap nor a spot pair is refused with a
warning and not listed, rather than labelled by guess.

Five services start together after a deploy, and the first of them to reach an empty catalog creates the
table; the others find it already made and carry on.

## When a pass fails

[[REQ-INFRA-012]]. The `worker` and `resample` run in a loop: a pass over the stored bars, a sleep, another
pass. A pass that fails (the object store answers 503 under load, a read races a writer) is reported with
the job's name, the exception and, **once per run of failures**, its traceback; later failures of the same
run are one line each with the count; and the first pass that succeeds says how many failed. The loop waits
its usual interval and tries again: the next pass is the retry, and a pass is cheap against its interval. A
pass over unchanged data writes nothing twice, so repeating it is safe.

Before this a failure of a pass's first read ended the process and compose restarted it, which happened
twice in one day for two unrelated reasons. A one-off run (`--once`) is not a loop and still fails loudly
and exits non-zero. Compose's restart policy stays as the last resort.

## Logs

An ingest service logs events and not traffic. INFO has connects, reconnects, recoveries
and one line for each archive object written; the per-trade lines are at DEBUG
(`CHANNELFLOW_LOG_LEVEL=DEBUG`). Before 2026-10-02 they were at INFO and Bybit's
container log reached 6.6 GB in six days.

Every service's container log is capped (`CHANNELFLOW_LOG_MAX_SIZE`,
`CHANNELFLOW_LOG_MAX_FILE`). A cap applies to a container when it is created, so changing it
takes effect on `docker compose up -d`.

## What timeframes a chart may offer

`GET /api/v1/timeframes` reports what this deployment can serve
([[REQ-WP-074]]):

```json
{"timeframes":[
  {"token":"1m","timeframe_ns":60000000000},
  {"token":"5m","timeframe_ns":300000000000}
]}
```

The set is `CHANNELFLOW_TIMEFRAMES` plus `1m`. The source joins unconditionally:
the ingest daemon always writes it and §5.1 lists it, while the variable names
only what *resampling* builds ([[REQ-WP-073]]). A token the parser refuses — a
typo, or a calendar period like `1M` — refuses the API at startup exactly as it
refuses the resampler, so a misconfiguration is loud in both processes rather
than quiet in one.

The chart spends this read on its timeframe control: the options are what the
API reported, and a link naming anything else is refused on screen rather than
silently shown at a substituted timeframe.

## Observability

The API serves the Prometheus exposition at `/metrics` — outside `/api/v1`,
because it is operational rather than part of PRD §28's read API.

Prometheus scrapes it on the host at port 8000. Grafana loads one dashboard,
**generated** from `channelflow.observability` rather than written:

```
.venv/bin/python -m channelflow.observability.generate
```

A test fails if the committed file and the definition disagree, so a metric that
gains a producer fails the build until the dashboard is regenerated.

**Nine of the eleven metrics PRD §33 lists have no producer**, and the dashboard
says so in words rather than drawing them as empty graphs. A flat line at the
bottom of a chart reads as "nothing is going wrong", which is precisely what
nobody knows. See `REQ-WP-055`.

## The context collectors

[REQ-WP-093] Open interest, Funding (z) and Basis, three of the lower panes, have no data in a stack that
only ingests trades. `context-binance`, `context-bybit` and `context-okx` supply it: each polls its venue's
**public** REST endpoints every 60 seconds and stores what it saw in `derivatives_state`, append-only, with
the venue's time and the time we received it kept apart. They hold no key and compute no feature; the
worker does, once per pass, as of each bar's close ([[ADR-070]]).

What a series is shown, and from where:

| Series | Derivatives from | Why |
|---|---|---|
| Binance BTC/ETH/SOL (spot) | the same venue's **perpetual** of the same pair | a spot market has no open interest or funding; the association is declared once, in `channelflow/context/sources.py` |
| Bybit BTCUSDT, OKX BTC-USDT-SWAP | themselves | they are the perpetuals |

`basis_bps` is the perpetual's mark price against the venue's index (its spot composite). Open interest is
the figure the venue reports **in USD** -- Binance's from its five-minute history endpoint, because its
base-unit endpoint would need a price of our choosing. **`funding_z` is computed from settled funding only**:
the rates each venue's history reports, one per settlement, loaded at start and refreshed hourly, so the
24 settlements its window needs exist from the first start rather than eight days later. Polled funding is
the venue's still-revisable estimate and never enters it.

A value is as of the bar's close and uses only what the collector had **received** by then. Where a reading
is stale -- a poll older than three intervals (fifteen minutes for Binance's five-minute buckets), a
settlement older than one funding interval plus an hour -- or cannot be computed, **no row is written** and
the pane says "no data"; zero is never written for absence.

Each collector serves `/healthz` (200, or 503 once nothing has succeeded for three poll intervals) and
`/metrics` (`context_last_state_age_seconds`, `context_poll_failures_total`, `context_healthy`) on
`CONTEXT_BINANCE_PORT`, `CONTEXT_BYBIT_PORT` and `CONTEXT_OKX_PORT` (9101-9103, loopback by default), and
Prometheus scrapes them. A collector that stops is therefore visible; the panes it fed go back to "no data".

**Liquidations** ([REQ-WP-094]). Each collector also holds one websocket to its venue's public liquidation
stream (Binance `!forceOrder@arr` on the futures `/market/ws/` path -- the legacy `/ws/` path connects and
says nothing; Bybit `allLiquidation.<symbol>`; OKX `liquidation-orders`) and stores each event in
`liquidations`. **The side is the position that was closed**: Binance and OKX publish the closing *order's*
side (a forced SELL liquidates a long), Bybit publishes the position's side (a Buy is a long); the three
mappings are pinned by tests. OKX reports contracts, converted with the instrument's own contract value.

The stream task also writes a **heartbeat** per symbol per minute, but only for a minute in which its
connection stayed up from the start of the minute to the end. The worker writes the three liquidation
features (long and short USD over the trailing five minutes, and their imbalance) only for a window
whose every minute has a heartbeat: **zero liquidated is a reading only where the stream was listening**,
and the imbalance of a quiet window is absent, not zero. Intensity and time-since-spike are registered
but not produced. A quiet stream is not reconnected for being quiet (Binance's 60 s silence limit is off
for this stream; its keepalive is not).

**The order book** ([REQ-WP-095]). Each collector holds a book stream too -- Binance's **spot** partial depth
(`<symbol>@depth10@1000ms`; the Binance series are spot markets), Bybit's linear `orderbook.50`, OKX's `books`
(its 400-level channel: `books5` has five levels and ten are asked for; OKX sizes are contracts and are
converted to base units). The raw book is **not stored**: the existing `BookService` and `OFITracker` run
inside the collector and, when a minute ends in event time, one row is stored in `book_minutes` -- the
one-minute order-flow imbalance, the ten-level depth imbalance and the top-of-book quote -- with the number of
frames and observations it rested on. The same minute writes a row to `quotes`, which is what the cross-venue
consensus is a median of.

A minute is finalised from the book **as it was before the first message of the next minute**, so it contains
nothing the market had not shown by then; a minute with no frame is stored with a count of zero and nothing
else, and the worker writes no feature for it. The tracker is fed the top of the book **once a second of event
time** whatever rate the venue pushes at, so every venue's OFI is the same measurement -- a sampled one, which
the feature's registration says: it is not the exchange's event-level figure. A reconnect or a lost sequence
breaks the flow baseline, and a lost sequence makes the connection be remade for a fresh snapshot. A book with
fewer than ten levels a side gets no ten-level imbalance, and a crossed book is not a quote.

The worker writes `ofi_1m` and `depth_imbalance_10` from the latest minute that ended at or before the bar's
close and is no more than two minutes old. `CHANNELFLOW_CONTEXT_STREAMS` (default `liquidations,book`; an empty
value turns every stream off) chooses what a collector holds beside its polls.

**A second spot venue** ([REQ-WP-098]). OKX spot is ingested like every other market (one process per symbol), its
books are collected by the OKX collector, and each spot asset's group is now Binance and OKX, so the consensus has
two venues and the Binance spot venue-basis pane has a line. **A spot book's sizes are base units and a swap's are
contracts**: the OKX book stream asks the instrument which it has -- `BASE-QUOTE` is spot, `BASE-QUOTE-SWAP` is a
swap -- and converts only the swap's. A spot series is shown its venue's perpetual of the same pair for open interest,
funding and basis (named in `channelflow/context/sources.py`, with the one list of series), so the OKX collector also
polls `ETH-USDT-SWAP` and `SOL-USDT-SWAP`. Three more series make the worker's cycle longer: more channels, signals and
notary records per cycle.

**The DEX panes** ([REQ-WP-099]). One more service, `context-hyperevm`, reads HyperEVM's public JSON-RPC
(`CHANNELFLOW_DEX_RPC_URL`; the default node needs no key) for the two busiest WHYPE/USDC pools on chain 999 -- a
Uniswap v3 pool and an Algebra Integral pool, pinned in `channelflow/dex/hyperevm_pools.py` because they emit the
same `Swap` topic and are different protocols. Every 30 seconds it stores the swaps of the blocks it has not yet
read in `dex_swaps` and, once caught up, one reading of each pool (liquidity, price, fee) in `dex_state`. The node
refuses `eth_getLogs` over 1000 blocks and rate-limits within seconds of a burst -- inside an HTTP 200 -- so a gap
is asked for in pieces, a few per poll, and a failed request stores nothing and moves nothing. A restart resumes after
the last stored block. The features are written for **both HYPE perpetuals** -- Bybit's and OKX's, ingested for the purpose
(`ingest-bybit-hype`, `ingest-okx-hype`) because HyperEVM has no bars, and two so that the venue-basis pane of the HYPE
series has a two-venue consensus: swap imbalance over the trailing five minutes (both pools) and the
Uniswap v3 pool's active liquidity. A window in which the collector did not read every pool in every minute has **no**
imbalance -- a quiet minute is a fact only where the collector was there -- and neither has a window with no swap.
`CONTEXT_HYPEREVM_PORT` (9104) serves `/healthz` and `/metrics`.

**The consensus** ([REQ-WP-096]). The worker turns the quotes into the cross-venue consensus: one `consensus`
row per minute close (every bar close is one), by the library's own median, a refusal stored with its reason and
no price. Consensus is per asset and market type, never blended: Bybit and OKX BTC are both perpetuals and form
one group; Binance's and OKX's spot series form the spot groups (two venues each, since [REQ-WP-098]); a group with one
venue is refused for that minute, and the venue-basis pane says so. The API asks for a consensus by the
viewed venue's symbol, so a group is stored under every symbol its members use (Bybit's BTCUSDT and OKX's BTC-USDT-SWAP).
`make panes-report` reads the running API and prints, for every market and timeframe, each lower pane as `data`,
`absent` with the reason the system gave, or `no-producer` (empty, and nothing says why: exit 1).

Start them without recreating anything else:

```
docker compose up -d --no-deps context-binance context-bybit context-okx context-hyperevm
```

and read each one's log first (`docker logs channelflow-context-bybit-1`).

## The live chart ([REQ-WP-102])

The bars table is written fifteen bars at a time (fewer commits keep the file count, and so the read cost, down), so a
one-minute chart read from it is up to fifteen minutes behind. The chart therefore has its own feed. Each ingest daemon
publishes the 1m bar it is **building** (at most once a second) and every bar it **finishes** to Redpanda
(`market.bar_live.v1`, thirty minutes' retention, created on first use); the API reads the topic from the start on every
start, keeps the last thirty minutes of each series, and relays them on a WebSocket at `/api/v1/live` -- first the cached
bars (the stretch the table has not caught up on), then every update. The page draws them after the last stored bar,
updates the forming candle in place, and says **live** or **delayed**; it reconnects with backoff and keeps reloading on a
timer while the socket is down.

It is a view, not the record: publishing is best effort (a broker that is down is counted and the ingest carries on, and
neither the ingest nor the API waits for it), a forming bar is marked `is_final: false` end to end, is never stored and no
feature reads it, and a final bar is never replaced by a forming one. Only the 1m timeframe is live; the others reload.

The socket is the one a browser may use, and it is **gated like everything under `/api/v1/`**: with Telegram
authentication required it takes the launch data as a WebSocket subprotocol (`tma`, then the data base64url-encoded --
a header cannot be set on a browser WebSocket and a URL is logged) and is closed (1008) without a valid one. The route
PRD §28.7 names, `/ws/market`, stays closed to the browser in that mode, and the public proxy still has one location.

## The signal notary (Monad testnet)

[REQ-INFRA-006] A small contract, `contracts/src/SignalNotary.sol`, records that a hash was committed
and later what became of it. It is a notary of this system's own decisions: one account writes, a hash
is committed once and resolved once, and nothing can be edited afterwards. What is hashed and when is
[REQ-INFRA-007]; this section is only the contract and how to deploy and check it.

A commit proves the hash existed **no later than its block**. It does not prove a signal came before a
price move, and the contract keeps the bar's close time (as claimed by the committer) and the block time
as two separate values.

    make contracts-test                         # the Solidity suite, offline once solc is cached
    python -m tools.notary.deploy               # dry run: what would be sent; nothing is
    python -m tools.notary.deploy --broadcast   # deploy; writes deployments/monad-testnet.json last
    make notary-verify                          # re-read the deployment from the chain
    python -m tools.notary.smoke                # one real commit and resolve

Configuration is in `.env.example` under "signal notary". The signer is a Foundry keystore account and
a file holding its password; the key is never on a command line and never in the environment:

    cast wallet import notary-deployer -i       # once, at a terminal; the key is typed, not passed
    export MONAD_SIGNER_ACCOUNT=notary-deployer
    export MONAD_SIGNER_PASSWORD_FILE=/path/outside/the/repo/keystore.pass   # mode 600

| Variable | Meaning |
|---|---|
| `MONAD_RPC_URL` | The node to talk to; defaults to the published Monad testnet endpoint |
| `MONAD_CHAIN_ID` | The chain id the node must report (10143 for Monad testnet); anything else is refused |
| `MONAD_EXPLORER_URL` | Base for transaction links, `<base>/tx/<hash>` |
| `MONAD_SIGNER_ACCOUNT` | Name of the Foundry keystore account that signs (required) |
| `MONAD_SIGNER_PASSWORD_FILE` | Path of the file holding that keystore's password (required) |
| `MONAD_NOTARY_OWNER` | The one account the contract lets write; empty means the signer's own address |
| `MONAD_NOTARY_ADDRESS` | The deployed contract; set only after a deployment was read back from the chain |

The deploy refuses to run against a chain id other than `MONAD_CHAIN_ID`, refuses `--broadcast` with
uncommitted changes in `contracts/`, and writes the record only after the receipt, the created address,
the on-chain code (hashed and compared with a fresh local compile) and `owner()` have all been read
back. If the testnet is reset the recorded address stops resolving and `make notary-verify` says so;
the contract is then redeployed from the same source.

### Notarizing the records ([[REQ-INFRA-007]])

The `worker` registers each snapshot and decision it computes and holds no key; the `notary` service
batches them, signs one root per window and sends it. What a commit proves, and the measured delay, are
in [notary.md](notary.md). It is off until switched on, and a stack without keys never runs it.

    eval "$(make -s notary-build-info)"        # the commit and whether the tree was clean, for this build
    docker compose up -d --no-deps --build worker notary
    docker compose exec notary python -m channelflow.notary.main outbox     # what waits, and why

| Variable | Meaning |
|---|---|
| `CHANNELFLOW_NOTARY_ENABLED` | the worker registers records only when this is true |
| `CHANNELFLOW_NOTARY_FROM` | the instant from which records are notarized (ISO-8601 with a timezone); required when enabled, no default; set **once** in `.env` — a value exported at deploy time overrides it and moves the epoch, leaving records unregistered |
| `CHANNELFLOW_CODE_COMMIT` | the commit the images were built from (a build argument; the container has no `.git`) |
| `CHANNELFLOW_CODE_DIRTY` | `false` if the tree was clean; anything else makes records unnotarizable, visibly |
| `MONAD_KEYSTORE_FILE` | host path of the Foundry keystore the `notary` service signs with; read-only, owned by uid 10001, mode 400, outside the repository |
| `MONAD_NOTARY_DEPLOY_BLOCK` | the block the contract was deployed in, where the log search for a commit begins |
| `CHANNELFLOW_NOTARY_BATCH_WINDOW` | how long a record may wait before its batch is formed (default `30m`) |
| `CHANNELFLOW_NOTARY_INTERVAL` | how often the service ticks (default 60 seconds) |
| `CHANNELFLOW_NOTARY_MAX_BATCH` | the most records in one batch (default 5000) |
| `CHANNELFLOW_NOTARY_MIN_BALANCE` | in wei; below it nothing is sent and the batch is held with the reason |
| `CHANNELFLOW_NOTARY_MAX_GAS_PRICE` | in wei; above it nothing is sent |
| `CHANNELFLOW_NOTARY_GAS_MARGIN` | the gas limit is the estimate times this; Monad bills the limit, so slack is paid for |
| `CHANNELFLOW_NOTARY_SUBMIT_TIMEOUT` | how long a sent transaction may go without a receipt before it is looked at again |
| `NOTARY_METRICS_PORT` | the host port for the notary's `/metrics` (loopback only, like the others) |

The service starts only if the node is on `MONAD_CHAIN_ID` and the signing address is the contract's
owner; otherwise it exits saying why. It never tops up its own balance.

The owner key cannot be rotated. A leaked key is remedied by a new contract and a retired old one, not
by a feature.

## What this stack deliberately does not run

PRD §6.2's MVP list names services this deployment does not have, each for a
recorded reason:

| §6.2 names | why not |
|---|---|
| `clickhouse` | [[ADR-002]] dropped it before any of it was built; the canonical plane is Iceberg |
| `redis` | listed as optional; nothing needs a cache, and [[ADR-018]] made alert delivery synchronous |

Pinot is in the target profile and not here: [[ADR-002]] defers it until a HOT
serving requirement exists, which is a gap Phase 4 still records rather than an
oversight.

## What is not covered

- **A process supervisor beyond Compose's `restart: unless-stopped`.**
- **TLS.** Nothing terminates it. This stack expects to be reached over an SSH
  tunnel or from behind something that does.
- **Authentication on the read API.** There is nothing to protect — every route
  is a `GET` — and [[REQ-WP-072]] makes adding a write route a deliberate act
  rather than building an auth scheme in advance of a user for one.
- **Backups.** `channelflow.lakehouse.backup` backs a table up and restores it
  where it came from ([[ADR-061]]); nothing schedules that.

Load tests are **no longer** on this list. `channelflow.perf.load` drives §36's
targets and reports a target it could not measure as *not measured* rather than
omitting it, which closed [[REQ-PHASE-8]]'s last acceptance line.
