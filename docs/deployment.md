# Running ChannelFlow

<!-- @trace: REQ-WP-056 -->
<!-- @trace: REQ-WP-072 -->

This describes what actually runs. It is checked against the repository by
`tests/unit/docs/test_deployment_doc.py`: every command named here is a real
`make` target, every service is in `docker-compose.yml`, and every variable is in
`.env.example`. A command renamed without this file changing fails that test
rather than leaving prose that is confident, plausible and wrong.

## What the stack is

Eleven services, started together:

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
| `maintenance` | prunes metadata, compacts and optionally expires, on a loop ([[REQ-WP-070]]) |

All six application services build from this repository ([[REQ-WP-064]],
[[REQ-WP-066]], [[REQ-WP-070]]) rather than pulling a tag naming a build nobody
in this checkout can reproduce. `worker` is the one §6.2 service with no
container, because it has no code: [[REQ-PIPE-001]] chose a replay over a daemon.

**Three ingest services, not one taking three symbols.** §5.1's Phase 1 universe
is BTCUSDT, ETHUSDT and SOLUSDT, and `ingest_main` refuses a configuration
naming more than one symbol: a daemon multiplexing several would share one
socket's failure across all of them, so one stalled symbol would stop the others
without saying so. The first keeps §6.2's bare spelling `ingest-binance`.

**What still has no producer.** Nothing in this stack fits a channel. The live
path is bars only, and `channel_snapshots` stays empty until [[REQ-WP-077]]
gives `record_replay` a process to run in. Measured 2026-09-17: 133 bars, zero
channel snapshots. Written here because a stack that looks complete and produces
no channels is the kind of thing a reader should learn from a document rather
than from an empty chart.

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
daemons, maintenance, Prometheus and Grafana, building the six application images from
this checkout rather than pulling a tag nobody here can reproduce.

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
| `http://localhost:8080` | the chart |
| `http://localhost:3000` | Grafana |

Add `-L 9001:127.0.0.1:9001` for the MinIO console if you want to see the
objects.

### 6. Check that it is actually working

```sh
docker compose logs --tail 20 ingest-binance     # frames arriving
curl -s localhost:8000/readyz                    # {"ready": true, ...}
docker compose exec -T minio sh -c 'ls /data/*/raw/cex/binance/*/*/*/ | tail -3'
```

The third is the raw archive — one gzip object per minute. If it is growing, the
socket is connected and the frames are being kept.

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
| `CHANNELFLOW_BIND_ADDRESS` | what every published port binds to; `127.0.0.1` by default ([[REQ-WP-072]]) |
| `CHANNELFLOW_CORS_ORIGINS`, `CHANNELFLOW_RATE_LIMIT`, `CHANNELFLOW_RATE_WINDOW_SECONDS` | what the read API allows and refuses |
| `GRAFANA_ADMIN_PASSWORD`, `GRAFANA_ANONYMOUS` | Grafana's credential; anonymous access is off unless enabled |
| `CHANNELFLOW_INGEST_SYMBOLS`, `CHANNELFLOW_INGEST_SYMBOLS_ETH`, `CHANNELFLOW_INGEST_SYMBOLS_SOL`, `CHANNELFLOW_INGEST_TIMEFRAME_NS` | what each ingest daemon reads, and at what bar size — one symbol per process |
| `CHANNELFLOW_MAINTENANCE_INTERVAL`, `CHANNELFLOW_KEEP_DAYS` | how often maintenance runs, and what it may expire |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | alert delivery, empty unless alerting is wanted |
| `CHANNELFLOW_CHART_BASE_URL` | where an alert's chart link points |

The credentials in `.env.example` are development defaults and say so in their
values. PRD §34 requires the Telegram token to come from a secret manager in
anything that is not a laptop, and nothing in this repository reads it from the
environment on its own: the transport and its credentials are supplied by the
caller ([[ADR-018]]).

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

## What this stack deliberately does not run

PRD §6.2's MVP list names services this deployment does not have, each for a
recorded reason:

| §6.2 names | why not |
|---|---|
| `clickhouse` | [[ADR-002]] dropped it before any of it was built; the canonical plane is Iceberg |
| `redis` | listed as optional; nothing needs a cache, and [[ADR-018]] made alert delivery synchronous |
| `worker` | does not exist as code: [[REQ-PIPE-001]] chose a replay over a daemon deliberately, and a container running nothing reports healthy |

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
