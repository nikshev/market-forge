# @trace: REQ-WP-097
"""Ask the running API what it holds, and parse the page's own list of panes.

The pane list is read from `apps/web/src/panes.ts` -- the page is the authority on what it shows,
and a copy kept here would be one more list to forget to update."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]

#: `(path, query parameters) -> (HTTP status, decoded JSON or None)`. A fake in tests.
Get = Callable[[str, dict[str, str]], tuple[int, Any]]


class ApiUnreachable(RuntimeError):
    """The API did not answer at all; distinct from an answer that says 'no'."""


def http_get(base: str, *, timeout: float = 30.0) -> Get:
    client = httpx.Client(base_url=base, timeout=timeout)

    def get(path: str, params: dict[str, str]) -> tuple[int, Any]:
        try:
            response = client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise ApiUnreachable(f"{base}{path}: {type(exc).__name__}: {exc}") from exc
        try:
            body = response.json()
        except ValueError:
            body = None
        return response.status_code, body

    return get


def panes_from_page(path: Path | None = None) -> list[tuple[str, str]]:
    """`(feature, label)` for every pane the page offers, volume first as the page lists them."""
    source = (path or ROOT / "apps" / "web" / "src" / "panes.ts").read_text()
    pairs = re.findall(r'\{\s*feature:\s*"([a-z0-9_]+)",\s*label:\s*"([^"]+)"\s*\}', source)
    if not pairs:
        raise ValueError("no pane found in panes.ts: has its format changed?")
    # BAR_PANES comes after PANES in the file but is shown first: the page's ROW puts it ahead.
    return sorted(pairs, key=lambda pair: pair[0] != "volume")
