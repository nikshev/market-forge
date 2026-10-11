"""Fixtures for the collector's tests."""

from __future__ import annotations

import pytest

from tests.unit.context.doubles import FakeClient


@pytest.fixture
def client() -> FakeClient:
    return FakeClient()
