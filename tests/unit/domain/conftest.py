"""Regeneration switch for the golden fixtures."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--regenerate-fixtures",
        action="store_true",
        default=False,
        help="Rewrite the committed domain fixtures instead of comparing against them.",
    )
