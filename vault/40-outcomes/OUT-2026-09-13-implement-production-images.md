---
id: OUT-2026-09-13-implement-production-images
step: implement
records: [REQ-WP-064]
commit: null
---

## What was done

`api/main.py`, `api/readiness.py`, a `Dockerfile` for the API and one for the web
app, `api` and `web` in compose, and a CI step that builds both and probes the
running API. 18 tests, **13 of 13 mutants caught**.

## The missing piece was not a Dockerfile

`create_app` takes an already-built repository; `LakehouseRepository` takes a
`Catalog`; the only place a catalog was opened was a test fixture pointing at a
temporary directory. **Nothing in this project could be started as a process.**

The catalog factory already took a PostgreSQL URI and an S3 warehouse and
deliberately does not branch on the scheme ([[REQ-WP-041]]), so what was missing
was the part that reads the environment and calls it.

Nothing in it defaults. The convenient default is a local directory, and a
process serving an empty warehouse looks exactly like a market where nothing
happened — this system's most dangerous shape, met again.

## Two failures that only running could find

**An editable install.** `uv sync` installs the project with a path link to the
build stage's `/src`, and the runtime stage copies only the virtualenv. The image
built, the container started, and `uvicorn` reported
`No module named 'channelflow'`. Fixed with `--no-editable`.

**The wrong driver.** I wrote `postgresql+psycopg2://` into the compose file; this
project depends on `psycopg` 3, and its own integration test has used
`postgresql+psycopg://` all along. The container started and died on
`No module named 'psycopg2'`.

Both produce an image that builds cleanly and a service that cannot serve. That
is why CI now builds the images **and starts one** — a Dockerfile that is never
built is a document, and one that is built but never run is a slightly longer
document.

## Readiness is not §32's health, and not a ping

[[REQ-WP-035]]'s `HealthState` grades feeds: a stale book disqualifies a signal.
A container probe asks whether this process can serve. Sharing an endpoint would
have an orchestrator restart a pod because a venue went quiet, and would call a
process that cannot reach its catalog healthy whenever the feeds were fine.

A ping would be no better: a process that started and cannot read its warehouse
serves empty results. So the probe asks the catalog to name what it holds.
Measured: stopping PostgreSQL turns `/readyz` into 503 carrying the cause, and
starting it returns 200.

## The sweep found two tests that pinned themselves

`REQUIRED` shortened to one variable survived, because the parametrised test took
its cases **from `REQUIRED`** — removing the entry removed the case that would
have caught it. `NOT_READY = 503` changed to `200` survived, because the test
asserted `status_code == NOT_READY`, comparing a response against the value that
produced it.

The same flaw twice: a test reading the constant it is supposed to pin. Both now
state the literal, and the parametrised test's own list is pinned separately.

## What is not containerised

§6.2 names `worker` and `ingest-binance`. **Neither exists as code.**
[[REQ-PIPE-001]] chose a replay over a daemon deliberately and said why; writing
a service to have something to put in an image would invert that. They stay named
and absent, in the compose file's comment and in the deployment document's table
of what this stack does not run.

`docs/deployment.md`'s guard from [[REQ-WP-056]] failed on this change — every
running service must be described and every variable documented — which is the
guard working, and the table it checks now lists `api`, `web`, `API_PORT` and
`WEB_PORT`.
