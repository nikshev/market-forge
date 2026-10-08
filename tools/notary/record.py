# @trace: REQ-INFRA-006
"""The deployment record: written last, read back by `verify` and `smoke`."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RECORD_PATH = ROOT / "deployments" / "monad-testnet.json"


def read(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text()) if path.exists() else None


def write(path: Path, record: dict[str, Any]) -> None:
    """Atomically: a reader sees the old file or the whole new one, never half."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def solc_version(contracts_dir: Path) -> str:
    for line in (contracts_dir / "foundry.toml").read_text().splitlines():
        if line.startswith("solc_version"):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("foundry.toml pins no solc_version")
