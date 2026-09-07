"""Command line entry point. The only module here that prints or chooses exit codes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.trace.dashboard import (
    render_requirement_trace,
    update_requirement_notes,
    write_dashboard,
)
from tools.trace.graph import build_graph, write_json
from tools.trace.validate import validate

EXIT_OK = 0
EXIT_VIOLATIONS = 1
EXIT_USAGE = 2


def _parser() -> argparse.ArgumentParser:
    # --repo-root lives on a parent parser so it is accepted after the subcommand,
    # which is where it reads naturally: `trace validate --repo-root .`
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--repo-root", type=Path, default=Path.cwd(), help="Repository root (default: cwd)"
    )

    parser = argparse.ArgumentParser(prog="trace", description="ChannelFlow traceability graph")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", parents=[common], help="Rebuild .trace/graph.json")
    sub.add_parser("validate", parents=[common], help="Check coverage rules; exit 1 on violations")
    sub.add_parser(
        "dashboard",
        parents=[common],
        help="Regenerate the dashboard and requirement Trace sections",
    )
    show = sub.add_parser("show", parents=[common], help="Print what links to one requirement")
    show.add_argument("requirement", help="Requirement id, e.g. REQ-WP-001")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.repo_root)

    try:
        graph = build_graph(root)
    except ValueError as exc:
        print(f"trace: cannot build graph: {exc}", file=sys.stderr)
        return EXIT_VIOLATIONS

    if args.command == "build":
        target = root / ".trace" / "graph.json"
        write_json(graph, target)
        print(f"trace: wrote {target} ({len(graph.nodes)} nodes, {len(graph.edges)} edges)")
        return EXIT_OK

    if args.command == "validate":
        violations = validate(graph)
        if not violations:
            print(f"trace: clean ({len(graph.nodes)} nodes, {len(graph.edges)} edges)")
            return EXIT_OK
        for violation in violations:
            print(f"{violation.rule}  {violation.node_id}  {violation.message}")
        print(f"\ntrace: {len(violations)} violation(s)")
        return EXIT_VIOLATIONS

    if args.command == "dashboard":
        violations = validate(graph)
        dashboard_path = root / "vault" / "00-index" / "Traceability Dashboard.md"
        try:
            write_dashboard(graph, violations, dashboard_path)
        except ValueError as exc:
            print(
                f"trace: cannot write dashboard {dashboard_path}: marker pair looks wrong: {exc}",
                file=sys.stderr,
            )
            return EXIT_VIOLATIONS
        updated, skipped = update_requirement_notes(graph)
        print(f"trace: dashboard written, {len(updated)} requirement note(s) refreshed")
        for path in skipped:
            print(f"trace: warning: no trace markers in {path}", file=sys.stderr)
        return EXIT_OK

    if args.command == "show":
        if args.requirement not in graph.nodes:
            print(f"trace: unknown requirement {args.requirement!r}", file=sys.stderr)
            return EXIT_USAGE
        print(args.requirement)
        print(render_requirement_trace(graph, args.requirement))
        return EXIT_OK

    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
