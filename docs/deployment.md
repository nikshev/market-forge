# Running ChannelFlow

<!-- @trace: REQ-WP-056 -->
<!-- @trace: REQ-WP-072 -->

This describes what actually runs. It is checked against the repository by
`tests/unit/docs/test_deployment_doc.py`: every command named here is a real
`make` target, every service is in `docker-compose.yml`, and every variable is in
`.env.example`. A command renamed without this file changing fails that test
rather than leaving prose that is confident, plausible and wrong.

## What the stack is

Nine services, started together:

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
| `maintenance` | prunes metadata, compacts and optionally expires, on a loop ([[REQ-WP-070]]) |

All four application services build from this repository ([[REQ-WP-064]],
[[REQ-WP-066]], [[REQ-WP-070]]) rather than pulling a tag naming a build nobody
in this checkout can reproduce. `worker` is the one §6.2 service with no
container, because it has no code: [[REQ-PIPE-001]] chose a replay over a daemon.

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
| `CHANNELFLOW_INGEST_SYMBOLS`, `CHANNELFLOW_INGEST_TIMEFRAME_NS` | what the ingest daemon reads, and at what bar size |
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
