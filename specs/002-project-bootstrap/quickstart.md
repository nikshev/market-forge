# Quickstart: local development stack

What SC-001 is measured against — from a clean checkout to a running stack, with
no manual steps beyond what is listed here.

## Prerequisites

- A container runtime: Docker Desktop, OrbStack, Podman, or Colima.
- `uv` for the Python environment.

Installing either is out of scope for this project.

## Start

```bash
cp .env.example .env      # development-only defaults; edit only if a port clashes
make up
```

`make up` brings up PostgreSQL and MinIO and does not return success until both
report healthy. Running it again against a running stack is safe and changes
nothing.

## Verify

```bash
make test                 # includes the integration test that connects to both services
```

The integration test is the real check: it opens a connection to PostgreSQL and
runs a query, and lists buckets against MinIO. If `make up` succeeded but this
fails, the stack is up but not usable, which is the case a naive start would
have hidden.

## Stop

```bash
make down                 # stops the services; data volumes survive
make reset                # stops AND deletes the volumes -- destructive
```

`make down` then `make up` preserves anything written in between. `make reset`
does not, and is the only command here that discards data.

## Quality gate

```bash
make lint                 # ruff check + ruff format --check
make typecheck            # mypy --strict over src/
make test                 # pytest
make validate             # traceability coverage
```

All four pass on a clean checkout. A red result is your change, not the
environment — that is the property SC-003 protects.

## When something goes wrong

- **A port is already in use**: `make up` names the port and the service. Change
  it in `.env`; the compose file reads the value rather than hardcoding it.
- **The container runtime is not running**: `make up` says so rather than
  failing with an opaque error from the orchestration tool.
- **The stack came up but the integration test fails**: the services are running
  but not answering. Check `docker compose ps` for health status, and the
  service logs for a startup error.
