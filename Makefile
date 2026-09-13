VENV := .venv
PY   := $(VENV)/bin/python
PIP  := uv pip install --python $(PY)

.PHONY: venv install test lint markers trace validate dashboard graph clean index mutate \
	web-install web-typecheck web-test web-build

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

lint:
	$(VENV)/bin/ruff check tools tests src
	$(VENV)/bin/ruff format --check tools tests src

typecheck:
	$(VENV)/bin/mypy

# Local development stack (REQ-WP-001). `up` does not return success until
# every service is healthy -- a started container is not a ready service.
# --wait names only the long-running services: it treats a one-shot container
# that exited 0 as a failure, so minio_init runs as a separate step.
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
