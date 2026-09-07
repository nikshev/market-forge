VENV := .venv
PY   := $(VENV)/bin/python
PIP  := uv pip install --python $(PY)

.PHONY: venv install test lint markers trace validate dashboard graph clean index

venv:
	uv venv $(VENV) --python 3.12 --no-python-downloads

install: venv
	$(PIP) -e ".[dev]"

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

dashboard: markers
	$(PY) -m tools.trace.cli dashboard

graph: trace dashboard

clean:
	rm -rf .trace .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

index:
	$(VENV)/bin/graphify . --update
