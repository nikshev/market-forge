# Running ChannelFlow

<!-- @trace: REQ-WP-056 -->

This describes what actually runs. It is checked against the repository by
`tests/unit/docs/test_deployment_doc.py`: every command named here is a real
`make` target, every service is in `docker-compose.yml`, and every variable is in
`.env.example`. A command renamed without this file changing fails that test
rather than leaving prose that is confident, plausible and wrong.

## What the stack is

Five containers, started together:

| service | what it is for |
|---|---|
| `postgres` | transactional metadata and the Iceberg catalog |
| `minio` | the S3-compatible object store the canonical plane writes to |
| `redpanda` | the Kafka-protocol event backbone |
| `prometheus` | scrapes the API's exposition |
| `grafana` | renders the dashboard generated from the code |
| `api` | the read API of PRD §28, built from this repository ([[REQ-WP-064]]) |
| `web` | the chart application, static files behind nginx, which proxies `/api` to `api` |

The API, the web app and any worker run **from the host** in development. They
are not containerised here, and that is a gap rather than a decision: nothing has
needed a production image yet, and writing one before there is somewhere to
deploy it would be guessing at a base image and a process supervisor.

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
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | alert delivery, empty unless alerting is wanted |
| `CHANNELFLOW_CHART_BASE_URL` | where an alert's chart link points |

The credentials in `.env.example` are development defaults and say so in their
values. PRD §34 requires the Telegram token to come from a secret manager in
anything that is not a laptop, and nothing in this repository reads it from the
environment on its own: the transport and its credentials are supplied by the
caller ([[ADR-018]]).

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
| `worker`, `ingest-binance` | neither exists as code: [[REQ-PIPE-001]] chose a replay over a daemon deliberately, and a container running nothing reports healthy |

Pinot is in the target profile and not here: [[ADR-002]] defers it until a HOT
serving requirement exists, which is a gap Phase 4 still records rather than an
oversight.

## What is not covered

- **Production images and a supervisor.** Nothing is containerised beyond the
  stateful services.
- **Load tests.** Phase 8's remaining item, and it needs something deployed to
  load.
- **Backups.** `channelflow.lakehouse.backup` backs a table up and restores it
  where it came from ([[ADR-061]]); nothing schedules that.
