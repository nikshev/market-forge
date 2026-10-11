VENV := .venv
PY   := $(VENV)/bin/python
PIP  := uv pip install --python $(PY)

.PHONY: venv install test lint markers trace validate dashboard graph clean index mutate \
	web-install web-typecheck web-test web-build contracts-test notary-verify \
	notary-build-info images-resolvable

venv:
	uv venv $(VENV) --python 3.12 --no-python-downloads

# --frozen installs exactly what uv.lock pins. `uv pip install -e` would
# resolve afresh and quietly ignore the lockfile, which is how CI and a
# developer's machine drift onto different versions of the same tool.
install:
	uv sync --frozen --extra dev --extra tooling

test:
	$(PY) -m pytest -q

# The fast gate: everything that needs no live service. This is what the
# pre-commit hook runs, so committing does not require a container runtime.
# The full gate -- including integration tests and traceability coverage --
# runs in CI. See REQ-INFRA-002.
test-fast:
	$(PY) -m pytest -q -m "not integration"

# The Solidity suite of the signal notary (REQ-INFRA-006). It also runs inside `make test`
# through tests/contracts, which is what makes it visible to the trace graph; this target is
# the quick way to see forge's own output. Needs Foundry (`foundryup`).
contracts-test:
	cd contracts && forge test

# Re-read the recorded Monad deployment from the public RPC and compare it with the record and
# with a fresh compile. Exits 1 and says which check differs. Needs MONAD_SIGNER_* only to
# resolve the configuration; it sends nothing.
notary-verify:
	$(PY) -m tools.notary.verify

# Does every container image the repository names still resolve at its registry? (REQ-INFRA-013)
# Reads docker-compose.yml, the Dockerfiles and the CI workflows, asks each registry, and exits 1
# naming any image that is no longer served. CI runs it before its first pull. Not in the pre-commit
# hook: it needs a network, and that hook's contract is that it does not.
images-resolvable:
	$(PY) -m tools.images

# What the notary needs from a build (REQ-INFRA-007): the commit the images are built from and
# whether that tree was clean. Use as
#     eval "$(make -s notary-build-info)" && docker compose up -d --no-deps --build worker notary
# A dirty tree prints CHANNELFLOW_CODE_DIRTY=true, and the notary then stores its records as
# unnotarizable rather than hash a commit that names code that exists nowhere.
#
# It deliberately does NOT print the epoch (CHANNELFLOW_NOTARY_FROM). That is set once, in `.env`,
# when the notary is first enabled: printing it here let an exported value override `.env` on every
# deploy and move the epoch forward, leaving a permanent hole of records that were never registered.
notary-build-info:
	@echo "export CHANNELFLOW_CODE_COMMIT=$$(git rev-parse HEAD)"
	@if [ -z "$$(git status --porcelain)" ]; then echo "export CHANNELFLOW_CODE_DIRTY=false"; else echo "export CHANNELFLOW_CODE_DIRTY=true"; fi

lint:
	$(VENV)/bin/ruff check tools tests src
	$(VENV)/bin/ruff format --check tools tests src

typecheck:
	$(VENV)/bin/mypy

# Local development stack (REQ-WP-001). `up` does not return success until
# every service is healthy -- a started container is not a ready service.
# --wait names only the long-running services: it treats a one-shot container
# that exited 0 as a failure, so minio_init runs as a separate step.
compact:
	$(PY) -m channelflow.pipeline.maintenance_main

data-dirs:
	$(PY) -m tools.deploy.data_dir --root $${CHANNELFLOW_DATA_DIR:-./data}

up:
	@test -f .env || (echo "No .env found. Run: cp .env.example .env" && exit 1)
	docker compose up -d --wait postgres minio
	docker compose run --rm --no-deps minio_init

down:
	docker compose down

# The only destructive command here: removes the data volumes too.
reset:
	docker compose down -v

markers:
	@mkdir -p .trace
	@if $(PY) -m pytest -p tools.trace.pytest_plugin --trace-dump=.trace/tests.json -q \
	    > .trace/.markers-run.log 2>&1; then \
	    rm -f .trace/.markers-run.log; \
	else \
	    status=$$?; \
	    echo "trace: the test suite failed; a VERIFIES edge requires a test that"; \
	    echo "trace: actually passed, so markers cannot trust a red suite. Fix the"; \
	    echo "trace: failures below, then re-run (this is not an R2/R5 violation):"; \
	    echo; \
	    cat .trace/.markers-run.log; \
	    rm -f .trace/.markers-run.log; \
	    exit $$status; \
	fi

trace: markers
	$(PY) -m tools.trace.cli build

validate: markers
	$(PY) -m tools.trace.cli validate

# The acceptance audit: change the source in ways that should break something,
# and see whether anything breaks. Slower than the suite by the number of
# mutations -- about 1.7 seconds each -- so it is a step of its own rather than
# part of `test` (REQ-INFRA-004, ADR-065).
mutate:
	$(PY) -m tools.mutate

dashboard: markers
	$(PY) -m tools.trace.cli dashboard

graph: trace dashboard

# The frontend gates. ADR-021: these run in CI only -- `npm ci` on every commit
# would break the property REQ-INFRA-002 exists to protect, that the fast gate
# needs no heavy setup. They are `make` targets so CI calls exactly what a
# developer calls, which is what stops the two gates drifting.
WEB := apps/web

web-install:
	cd $(WEB) && npm ci

web-typecheck:
	cd $(WEB) && npx tsc --noEmit

web-test:
	cd $(WEB) && npx vitest run

web-build:
	cd $(WEB) && npx vite build

clean:
	rm -rf .trace .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

index:
	$(VENV)/bin/graphify . --update
