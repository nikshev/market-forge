"""PRD §29.0's rule, enforced rather than remembered.

    "Any backend-specific DDL must live behind migrations/adapters and must not
    leak into signal/channel domain code."

REQ-STORE-001.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[3] / "src" / "channelflow"

#: The packages PRD §29.0 names, plus the ones that would be the next to go: a
#: rule about "signal/channel domain code" is a rule about the code that decides
#: what a signal is, and the extrema, scoring and stop layers all do.
DOMAIN_PACKAGES = (
    "signals",
    "channels",
    "extrema",
    "scoring",
    "stops",
    "bars",
    "book",
    "features",
    "turning",
    "backtest",
)

#: What must not appear in them. `lakehouse` is this package; the other three
#: are the backends it exists to hide.
FORBIDDEN = ("channelflow.lakehouse", "pyarrow", "duckdb", "boto3")


def _imported_names(module: Path) -> set[str]:
    """Every module name the file imports, by parsing rather than by grepping.

    A substring search over the source would match the word `duckdb` in a
    docstring explaining why it is not imported -- which is exactly the sentence
    a module obeying this rule is likely to contain.
    """
    tree = ast.parse(module.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.trace("REQ-STORE-001")
@pytest.mark.parametrize("package", DOMAIN_PACKAGES)
def test_domain_code_does_not_reach_for_a_storage_backend(package: str) -> None:
    """The whole point of a port.

    A channel that imported pyarrow would be a channel that cannot be computed
    without a lakehouse, and PRD §29.0's substitution -- ClickHouse out,
    Iceberg in, the domain unchanged -- would stop being available.
    """
    directory = SRC / package
    modules = sorted(directory.rglob("*.py"))
    assert modules, f"{package} has no modules; this test would pass vacuously"

    for module in modules:
        imported = _imported_names(module)
        for name in imported:
            for forbidden in FORBIDDEN:
                assert not (name == forbidden or name.startswith(f"{forbidden}.")), (
                    f"{module.relative_to(SRC)} imports {name!r}; PRD §29.0 keeps "
                    "storage backends out of domain code so the backend can change "
                    "without it"
                )


@pytest.mark.trace("REQ-STORE-001")
def test_the_lakehouse_does_not_reach_back_into_the_domain() -> None:
    """The dependency points one way.

    A storage layer that imported the signal model would make the canonical
    plane specific to today's domain types, and PRD §29.B's seventeen tables
    span subsystems that do not know about each other.
    """
    modules = sorted((SRC / "lakehouse").glob("*.py"))
    assert modules, "the lakehouse package has no modules; this test would pass vacuously"

    for module in modules:
        for name in _imported_names(module):
            if not name.startswith("channelflow."):
                continue
            assert name.startswith("channelflow.lakehouse"), (
                f"{module.name} imports {name!r}; the canonical plane holds rows, "
                "and a row that had to be a domain object would tie every table to "
                "one subsystem"
            )
