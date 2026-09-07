VENV := .venv
PY   := $(VENV)/bin/python
PIP  := uv pip install --python $(PY)

.PHONY: venv install test lint markers trace validate dashboard graph clean

venv:
	uv venv $(VENV) --python 3.12 --no-python-downloads

install: venv
	$(PIP) -e ".[dev]"

test:
	$(PY) -m pytest -q

lint:
	$(VENV)/bin/ruff check tools tests
	$(VENV)/bin/ruff format --check tools tests

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
