"""Recorded Bybit traffic, replayed (REQ-WP-043).

PRD §35.6 requires connector tests to replay exchange sample messages. These
fixtures were captured once from the live public venue by
`tools/record/bybit_capture.py`; nothing here opens a socket, and nothing here
needed an account.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "bybit"


def _load(name: str) -> list[dict[str, Any]]:
    path = FIXTURES / f"{name}.jsonl"
    assert path.is_file(), f"missing fixture {path}; regenerate with tools.record.bybit_capture"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@pytest.fixture
def trade_messages() -> list[dict[str, Any]]:
    return _load("linear_publictrade_btcusdt")


@pytest.fixture
def book_messages() -> list[dict[str, Any]]:
    return _load("linear_orderbook_50_btcusdt")


@pytest.fixture
def rest_book() -> dict[str, Any]:
    return _load("rest_linear_orderbook")[0]
