# @trace: REQ-INFRA-013
"""`python -m tools.images`: does every image the repository names still resolve?

    python -m tools.images            # also: make images-resolvable

Exit 0: every image is served (or could not be asked about -- reported as unknown).
Exit 1: an image is no longer served, or a reference could not be read at all.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from tools.images.enumerate import enumerate_images
from tools.images.resolve import Runner, classify, docker_runner

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None, *, runner: Runner = docker_runner) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="the repository to read")
    args = parser.parse_args(argv)

    found = enumerate_images(args.root)
    where: dict[str, list[str]] = defaultdict(list)
    for ref in found.images:
        where[ref.reference].append(ref.where)

    gone = 0
    for reference in sorted(where):
        code, text = runner(reference)
        status = classify(code, text)
        places = "; ".join(sorted(set(where[reference])))
        if status == "served":
            print(f"served   {reference}")
        elif status == "unknown":
            first = (text.strip().splitlines() or ["no output"])[0][:120]
            print(f"unknown  {reference}  (could not be checked: {first})")
        else:
            gone += 1
            print(
                f"GONE     {reference}  -- no longer served by its registry; "
                f"referenced at: {places}"
            )

    for problem in found.unresolved:
        print(f"UNREAD   {problem}")

    print(
        f"\n{len(where)} image(s) named; {gone} no longer served; "
        f"{len(found.unresolved)} reference(s) could not be read."
    )
    return 1 if gone or found.unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
