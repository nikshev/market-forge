"""PRD §34, bullet by bullet (REQ-WP-072).

Seven of the section's eight requirements held before this file existed, and
five of them held because the thing that could break them had not been built.
That is not compliance; it is the absence of an opportunity. Each test here
fails the day the opportunity arrives.

The four bullets checked *here* are the ones about credentials never entering
the system in the first place. The other four are checked where the behaviour
is: `tests/unit/test_settings.py` (redaction), `tests/unit/api/test_security.py`
(write routes, CORS, rate limiting).
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "channelflow"

#: Environment names that would mean this system holds a credential it has no
#: business holding. §34's first bullet: public market data needs no trading key.
_TRADING_KEY = re.compile(
    r"API_SECRET|SECRET_KEY|TRADING_KEY|PRIVATE_KEY|API_PASSPHRASE", re.IGNORECASE
)


@pytest.mark.trace("REQ-WP-072")
def test_no_connector_reads_a_trading_credential() -> None:
    """§34: "no exchange trading keys required for public market data"."""
    connectors = sorted((SRC / "connectors").rglob("*.py"))
    assert len(connectors) > 10, "found almost no connector modules; check the path"
    for module in connectors:
        found = _TRADING_KEY.findall(module.read_text())
        assert not found, f"{module.relative_to(ROOT)} names {found}"


@pytest.mark.trace("REQ-WP-072")
def test_the_alerting_package_reads_no_environment() -> None:
    """§34: "Telegram bot token only via secret/env manager" ([[ADR-018]]).

    The package takes its transport and credentials from the caller. A module
    that read `os.environ` itself would be a second place a token could be
    configured, and the one nobody remembers to rotate.
    """
    modules = sorted((SRC / "alerting").rglob("*.py"))
    assert modules, "found no alerting modules; check the path"
    for module in modules:
        tree = ast.parse(module.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in {"environ", "getenv"}:
                pytest.fail(f"{module.relative_to(ROOT)} reads the environment")


@pytest.mark.trace("REQ-WP-072")
def test_no_rpc_endpoint_carries_a_key_in_its_url() -> None:
    """§34: "RPC API keys via secrets".

    Every endpoint this repository talks to is public and keyless. A key pasted
    into a URL would be committed, which is the next bullet.
    """
    recorders = sorted((ROOT / "tools" / "record").glob("*.py"))
    assert len(recorders) > 5, "found almost no capture tools; check the path"
    urls = []
    for module in recorders:
        urls.extend(re.findall(r'"(https://[^"]+)"', module.read_text()))
    assert urls, "found no endpoints at all; the check would pass vacuously"
    keyed = re.compile(r"[?&](api[-_]?key|apikey|key|token|secret|auth)=", re.IGNORECASE)
    for url in urls:
        # A query string is not the problem -- `?symbol=BTCUSDT` is data. A
        # parameter *named* like a credential is.
        assert not keyed.search(url), f"{url} passes a credential as a parameter"
        # A key pasted into the path, as several RPC providers ask for.
        assert not re.search(r"/[0-9a-fA-F]{24,}(/|$)", url), f"{url} has a key-shaped path"


@pytest.mark.trace("REQ-WP-072")
def test_the_environment_file_is_ignored_and_the_template_holds_no_live_secret() -> None:
    """§34: "no secrets committed"."""
    ignored = subprocess.run(  # noqa: S603
        ["git", "check-ignore", ".env"],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ignored.returncode == 0, ".env is no longer ignored by git"

    template = (ROOT / ".env.example").read_text()
    for line in template.splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if not value:
            continue
        assert "dev_only" in value or len(value) < 40, (
            f"{name} in .env.example carries {value!r}, which does not look like a placeholder"
        )
