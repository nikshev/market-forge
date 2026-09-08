"""Recorded Binance traffic, replayed (REQ-WP-003).

PRD section 35.6 requires connector tests to replay exchange sample messages.
These fixtures were captured once from the live venue by
`tools/record/binance_capture.py`; nothing here opens a socket.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "binance"


def _load(name: str) -> list[dict[str, Any]]:
    path = FIXTURES / f"{name}.jsonl"
    assert path.is_file(), f"missing fixture {path}; regenerate with tools.record.binance_capture"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@pytest.fixture
def agg_trades() -> list[dict[str, Any]]:
    return [m["data"] for m in _load("spot_btcusdt_aggTrade")]


@pytest.fixture
def trades() -> list[dict[str, Any]]:
    return [m["data"] for m in _load("spot_btcusdt_trade")]


@pytest.fixture
def depth_updates() -> list[dict[str, Any]]:
    return [m["data"] for m in _load("spot_btcusdt_depth_100ms")]


@pytest.fixture
def depth_snapshot() -> dict[str, Any]:
    return _load("rest_spot_depth_snapshot")[0]


@pytest.fixture
def premium_index() -> dict[str, Any]:
    return _load("rest_futures_premium_index")[0]


@pytest.fixture
def open_interest() -> dict[str, Any]:
    return _load("rest_futures_open_interest")[0]
