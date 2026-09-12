"""Write the Grafana dashboard the stack loads.

# @trace: REQ-WP-056

    .venv/bin/python -m channelflow.observability.generate

The file is generated rather than written, so it cannot disagree with the
definition it comes from. A test compares the two, which is what makes
regenerating it obligatory rather than remembered.
"""

from __future__ import annotations

from pathlib import Path

from channelflow.observability.grafana import render

DASHBOARD_PATH = (
    Path(__file__).resolve().parents[3] / "deploy" / "grafana" / "dashboards" / "channelflow.json"
)


def main() -> int:
    DASHBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_PATH.write_text(render())
    print(f"wrote {DASHBOARD_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
