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
	$(PY) -m pytest -p tools.trace.pytest_plugin --trace-dump=.trace/tests.json \
	    --collect-only -q > /dev/null

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
