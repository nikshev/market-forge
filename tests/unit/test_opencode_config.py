# @trace: REQ-INFRA-005
"""Test OpenCode configuration for ChannelFlow."""

import json
import subprocess

import pytest


@pytest.mark.trace("REQ-INFRA-005")
def test_opencode_config_validates():
    """OpenCode project config must validate against published schema."""
    result = subprocess.run(
        ["opencode", "debug", "config"],
        capture_output=True,
        text=True,
        cwd="/opt/market-forge",
        timeout=60,
    )
    assert result.returncode == 0, f"Config validation failed: {result.stderr}"
    config = json.loads(result.stdout)
    assert config.get("$schema") == "https://opencode.ai/config.json"


@pytest.mark.trace("REQ-INFRA-005")
def test_opencode_has_four_custom_agents():
    """OpenCode must discover all four ChannelFlow custom agents."""
    result = subprocess.run(
        ["opencode", "agent", "list"],
        capture_output=True,
        text=True,
        cwd="/opt/market-forge",
        timeout=60,
    )
    assert result.returncode == 0
    output = result.stdout
    for agent in ["architect", "implementer", "implementer-senior", "reviewer"]:
        assert agent in output, f"Missing agent: {agent}"


@pytest.mark.trace("REQ-INFRA-005")
def test_opencode_has_six_sdd_commands():
    """OpenCode must have all six SDD command entry points."""
    result = subprocess.run(
        ["opencode", "debug", "config"],
        capture_output=True,
        text=True,
        cwd="/opt/market-forge",
        timeout=60,
    )
    assert result.returncode == 0
    config = json.loads(result.stdout)
    commands = config.get("command", {})
    expected = [
        "sdd-requirement",
        "sdd-spec",
        "sdd-plan",
        "sdd-tasks",
        "sdd-implement",
        "sdd-trace",
    ]
    for cmd in expected:
        assert cmd in commands, f"Missing command: {cmd}"
        assert commands[cmd].get("template"), f"Command {cmd} has no template"


@pytest.mark.trace("REQ-INFRA-005")
def test_reviewer_is_read_only():
    """Reviewer agent must have edit: deny permission."""
    result = subprocess.run(
        ["opencode", "debug", "agent", "reviewer"],
        capture_output=True,
        text=True,
        cwd="/opt/market-forge",
        timeout=60,
    )
    assert result.returncode == 0
    config = json.loads(result.stdout)
    perms = config.get("permission", [])
    edit_denied = any(
        p.get("permission") == "edit" and p.get("action") == "deny"
        for p in perms
        if isinstance(p, dict)
    )
    assert edit_denied, "Reviewer must have edit: deny"


@pytest.mark.trace("REQ-INFRA-005")
def test_implementer_fallback_chain():
    """Implementer must have the configured fallback model chain."""
    result = subprocess.run(
        ["opencode", "debug", "agent", "implementer"],
        capture_output=True,
        text=True,
        cwd="/opt/market-forge",
        timeout=60,
    )
    assert result.returncode == 0
    config = json.loads(result.stdout)
    assert config.get("model", {}).get("modelID") == "mimo-v2.6-flash-free"
    fallbacks = config.get("options", {}).get("fallback_models", [])
    expected = [
        "opencode/nemotron-3.5-lightning-free",
        "opencode/ling-3.0-flash-fin-free",
        "opencode/muse-spark-1.3-contributor-free",
    ]
    assert fallbacks == expected


@pytest.mark.trace("REQ-INFRA-005")
def test_implementer_senior_fallback_chain():
    """Implementer-senior must have the configured fallback model chain."""
    result = subprocess.run(
        ["opencode", "debug", "agent", "implementer-senior"],
        capture_output=True,
        text=True,
        cwd="/opt/market-forge",
        timeout=60,
    )
    assert result.returncode == 0
    config = json.loads(result.stdout)
    assert config.get("model", {}).get("modelID") == "nemotron-3-ultra-free"
    fallbacks = config.get("options", {}).get("fallback_models", [])
    expected = [
        "opencode/muse-spark-1.3-contributor-free",
        "opencode/muse-spark-1.2-contributor-free",
        "opencode/big-pickle",
    ]
    assert fallbacks == expected


@pytest.mark.trace("REQ-INFRA-005")
def test_agents_md_has_required_rules():
    """AGENTS.md must contain all mandatory repository rules."""
    with open("/opt/market-forge/AGENTS.md") as f:
        content = f.read()

    required = [
        "draft → specified → planned",
        "tested → implemented → verified",
        "@pytest.mark.trace",
        "# @trace:",
        "No look-ahead",
        "hard_gated",
        "read-only",
        "replay parity",
    ]
    for rule in required:
        assert rule in content, f"Missing rule in AGENTS.md: {rule}"


@pytest.mark.trace("REQ-INFRA-005")
def test_no_foreign_terminology():
    """Created files must not contain Parts Search Orchestrator or FR-* references."""
    import glob

    files = glob.glob("/opt/market-forge/.opencode/**/*.md", recursive=True) + [
        "/opt/market-forge/AGENTS.md",
        "/opt/market-forge/opencode.json",
    ]
    forbidden = ["parts-agent", "Parts Search", "FR-"]
    for path in files:
        with open(path) as f:
            content = f.read()
        for term in forbidden:
            assert term not in content, f"Found '{term}' in {path}"
