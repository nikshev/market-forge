"""What of the Material UI interface can be checked without Node (REQ-WP-083).

# @trace: REQ-WP-083

The behaviour -- the theme, the scheme hook, the cards, the chart's colours, the roles and names
-- is tested by vitest (`make web-test`), which runs only in CI: ADR-021 keeps Node out of the
commit hook so that a commit touching no frontend file does not need a toolchain. A vitest test
cannot carry a pytest marker, so this file is the part of the requirement the fast gate can see
for itself, and it is only that part:

* FR-009: the eight screenshots exist, two pages by two schemes by two widths, at the sizes asked
  for;
* FR-001: the dependencies are declared, so `npm ci` in CI installs what the code imports;
* the logo is the favicon, and the file it points at exists;
* every new module carries its `@trace` marker (Principle XIV), so R8 can find the code.

It does not look at the screenshots. That was done by eye, and the outcome note records what it
found."""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "apps" / "web"
SHOTS = ROOT / "docs" / "ui"

PAGES = ("overview", "chart")
SCHEMES = ("light", "dark")
WIDTHS = {"desktop": 1280, "phone": 390}

NEW_MODULES = ("muiTheme.ts", "useScheme.ts", "MarketTypeChip.tsx", "AppShell.tsx")


def _png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    return struct.unpack(">II", header[16:24])


@pytest.mark.trace("REQ-WP-083")
@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("size", WIDTHS)
def test_there_is_a_screenshot_of_each_page_in_each_scheme_at_each_width(
    page: str, scheme: str, size: str
) -> None:
    path = SHOTS / f"{page}-{scheme}-{size}.png"

    assert path.is_file(), f"{path.relative_to(ROOT)} is missing"
    assert _png_size(path)[0] == WIDTHS[size]


@pytest.mark.trace("REQ-WP-083")
def test_no_screenshot_in_this_requirements_scheme_is_left_over_that_it_does_not_name() -> None:
    # Only files named in this requirement's own scheme (page-scheme-width). Other requirements keep
    # screenshots here under their own names and must not break this one by arriving.
    expected = {f"{p}-{s}-{z}.png" for p in PAGES for s in SCHEMES for z in WIDTHS}
    scheme = re.compile(rf"^({'|'.join(PAGES)})-({'|'.join(SCHEMES)})-[a-z]+\.png$")

    assert {p.name for p in SHOTS.glob("*.png") if scheme.match(p.name)} == expected


@pytest.mark.trace("REQ-WP-083")
def test_the_material_dependencies_are_declared_where_npm_ci_reads_them() -> None:
    package = json.loads((WEB / "package.json").read_text())["dependencies"]
    lock = json.loads((WEB / "package-lock.json").read_text())["packages"]

    for name in ("@mui/material", "@emotion/react", "@emotion/styled"):
        assert name in package, f"{name} is imported but not declared"
        assert f"node_modules/{name}" in lock, f"{name} is declared but not locked"


@pytest.mark.trace("REQ-WP-083")
def test_the_logo_is_the_favicon_and_the_file_it_names_is_served() -> None:
    html = (WEB / "index.html").read_text()

    match = re.search(r'<link rel="icon"[^>]*href="/([^"]+)"', html)
    assert match is not None, "index.html has no favicon link"
    assert (WEB / "public" / match.group(1)).is_file()


@pytest.mark.trace("REQ-WP-083")
@pytest.mark.parametrize("module", NEW_MODULES)
def test_every_new_module_names_the_requirement_it_serves(module: str) -> None:
    text = (WEB / "src" / module).read_text()

    assert "// @trace: REQ-WP-083" in text
