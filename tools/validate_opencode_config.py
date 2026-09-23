# @trace: REQ-INFRA-005
"""Validate OpenCode project configuration for ChannelFlow."""

import json
import subprocess
import sys


def main() -> int:
    """Validate OpenCode config resolves and has required agents/commands."""
    result = subprocess.run(
        ["opencode", "debug", "config"],
        capture_output=True,
        text=True,
        cwd="/opt/market-forge",
        timeout=60,
    )
    if result.returncode != 0:
        print(f"Config validation failed: {result.stderr}", file=sys.stderr)
        return 1

    config = json.loads(result.stdout)

    # Check required agents
    agents = config.get("agent", {})
    required_agents = {"architect", "implementer", "implementer-senior", "reviewer"}
    missing = required_agents - set(agents.keys())
    if missing:
        print(f"Missing agents: {missing}", file=sys.stderr)
        return 1

    # Check reviewer is read-only
    reviewer = agents.get("reviewer", {})
    perms = reviewer.get("permission", [])
    edit_denied = any(
        p.get("permission") == "edit" and p.get("action") == "deny"
        for p in perms
        if isinstance(p, dict)
    )
    if not edit_denied:
        print("Reviewer must have edit: deny", file=sys.stderr)
        return 1

    # Check required commands
    commands = config.get("command", {})
    required_commands = {
        "sdd-requirement",
        "sdd-spec",
        "sdd-plan",
        "sdd-tasks",
        "sdd-implement",
        "sdd-trace",
    }
    missing = required_commands - set(commands.keys())
    if missing:
        print(f"Missing commands: {missing}", file=sys.stderr)
        return 1

    # Check plugin
    plugins = config.get("plugin", [])
    if "@razroo/opencode-model-fallback" not in plugins:
        print("Missing @razroo/opencode-model-fallback plugin", file=sys.stderr)
        return 1

    print("OpenCode config validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())