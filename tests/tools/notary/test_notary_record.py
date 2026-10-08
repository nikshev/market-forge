# @trace: REQ-INFRA-006
"""The deployment record and `.env.example` agree, or both are absent (FR-011)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RECORD = ROOT / "deployments" / "monad-testnet.json"
ENV_EXAMPLE = ROOT / ".env.example"
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
KEY_SHAPE = re.compile(r"(?<![0-9a-fA-F])0x[0-9a-fA-F]{64}(?![0-9a-fA-F])")
FIELDS = {
    "chain_id", "address", "tx_hash", "block_number", "block_time", "owner", "deployer",
    "source_commit", "solc", "deployed_code_hash",
}  # fmt: skip


def _env_example_address() -> str | None:
    for line in ENV_EXAMPLE.read_text().splitlines():
        if line.startswith("MONAD_NOTARY_ADDRESS="):
            return line.split("=", 1)[1].strip() or None
    return None


@pytest.mark.trace("REQ-INFRA-006")
def test_the_record_and_env_example_agree_or_both_are_absent() -> None:
    address = _env_example_address()
    if not RECORD.exists():
        assert address is None, (
            "`.env.example` names a notary address but no deployment record exists"
        )
        return

    record = json.loads(RECORD.read_text())
    assert FIELDS <= set(record), f"record is missing {sorted(FIELDS - set(record))}"
    assert ADDRESS_RE.match(record["address"]) and record["chain_id"] == 10143
    assert address is not None, "a deployment record exists but `.env.example` carries no address"
    assert address.lower() == record["address"].lower()


@pytest.mark.trace("REQ-INFRA-006")
def test_env_example_documents_the_monad_variables() -> None:
    text = ENV_EXAMPLE.read_text()
    for name in (
        "MONAD_RPC_URL",
        "MONAD_CHAIN_ID",
        "MONAD_EXPLORER_URL",
        "MONAD_SIGNER_ACCOUNT",
        "MONAD_SIGNER_PASSWORD_FILE",
        "MONAD_NOTARY_OWNER",
        "MONAD_NOTARY_ADDRESS",
    ):
        assert re.search(rf"^{name}=", text, re.M), f"{name} is not documented in .env.example"
    assert "MONAD_DEPLOYER_KEY" not in text and "PRIVATE_KEY" not in text


@pytest.mark.trace("REQ-INFRA-006")
def test_no_tracked_file_holds_something_shaped_like_a_private_key() -> None:
    """A 32-byte hex value is a key, a hash or a transaction id; only a key must not be committed.

    Hashes and transaction ids legitimately appear (in the record, in fixtures); a private key does
    not appear *next to the word key*. So: no 64-hex value on a line that names a key, secret or
    mnemonic.
    """
    files = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.split(b"\0")
    offenders: list[str] = []
    for raw in files:
        path = ROOT / raw.decode()
        if not raw or path.suffix in {".png", ".svg", ".lock", ".parquet"} or not path.is_file():
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        if path == Path(__file__).resolve() or path.name in {"test_notary_chain.py"}:
            continue  # these name a dummy key on purpose
        for number, line in enumerate(text.splitlines(), 1):
            if KEY_SHAPE.search(line) and re.search(
                r"private[_ -]?key|secret|mnemonic|deployer_key", line, re.I
            ):
                offenders.append(f"{path.relative_to(ROOT)}:{number}")
    assert not offenders, f"a key-shaped value on a line naming a key: {offenders}"
