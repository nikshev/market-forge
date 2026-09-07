VENV := .venv
PY   := $(VENV)/bin/python
PIP  := uv pip install --python $(PY)

.PHONY: venv install test lint trace validate dashboard graph clean

venv:
	uv venv $(VENV) --python 3.12 --no-python-downloads

install: venv
	$(PIP) -e ".[dev]"

test:
	$(PY) -m pytest -q

lint:
	$(VENV)/bin/ruff check tools tests

trace:
	$(PY) -m tools.trace.cli build

validate:
	$(PY) -m tools.trace.cli validate

dashboard:
	$(PY) -m tools.trace.cli dashboard

graph: trace dashboard

clean:
	rm -rf .trace .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
