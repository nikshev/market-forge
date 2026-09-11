"""Recorded OKX traffic, replayed (REQ-WP-044).

Captured once from the live public venue by `tools/record/okx_capture.py`;
nothing here opens a socket and nothing needed an account.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "okx"


def _load(name: str) -> list[dict[str, Any]]:
    path = FIXTURES / f"{name}.jsonl"
    assert path.is_file(), f"missing fixture {path}; regenerate with tools.record.okx_capture"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@pytest.fixture
def trade_messages() -> list[dict[str, Any]]:
    return _load("swap_trades")


@pytest.fixture
def book_messages() -> list[dict[str, Any]]:
    return _load("swap_books")


@pytest.fixture
def interleaved() -> list[dict[str, Any]]:
    """Trades and book updates in the order they arrived.

    The only fixture that can say what `side` means: a trade's side is checked
    against the book as it stood when the trade came in, and per-channel files
    lose that.
    """
    return _load("swap_interleaved")


@pytest.fixture
def instruments() -> dict[str, Any]:
    return _load("rest_swap_instruments")[0]
