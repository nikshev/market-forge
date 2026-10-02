import os
import subprocess
from pathlib import Path

import pytest

from tools.trace.collect import (
    PRD_NODE_ID,
    collect_code,
    collect_decisions,
    collect_outcomes,
    collect_requirements,
    collect_specs,
)


def test_collects_one_node_per_requirement(vault):
    vault.requirement("REQ-WP-001")
    vault.requirement("REQ-WP-002")
    nodes, _ = collect_requirements(vault.vault)
    assert sorted(n.id for n in nodes) == ["REQ-WP-001", "REQ-WP-002"]
    assert {n.kind for n in nodes} == {"requirement"}


def test_requirement_carries_status_and_type_in_attrs(vault):
    vault.requirement("REQ-WP-001", status="implemented", type_="work-package")
    nodes, _ = collect_requirements(vault.vault)
    assert nodes[0].attrs["status"] == "implemented"
    assert nodes[0].attrs["type"] == "work-package"


def test_requirement_links_back_to_the_prd(vault):
    vault.requirement("REQ-WP-001", prd_ref="§46 WP-001")
    _, edges = collect_requirements(vault.vault)
    derived = [(e.src, e.dst) for e in edges if e.kind == "DERIVED_FROM"]
    assert derived == [("REQ-WP-001", PRD_NODE_ID)]


def test_depends_on_becomes_edges(vault):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-002", "REQ-WP-003"])
    _, edges = collect_requirements(vault.vault)
    deps = sorted(e.dst for e in edges if e.kind == "DEPENDS_ON")
    assert deps == ["REQ-WP-002", "REQ-WP-003"]


def test_gitkeep_and_templates_are_ignored(vault):
    (vault.vault / "10-requirements" / ".gitkeep").write_text("")
    vault.requirement("REQ-WP-001")
    nodes, _ = collect_requirements(vault.vault)
    assert len(nodes) == 1


def test_requirement_without_an_id_field_raises_naming_the_file(vault):
    bad = vault.vault / "10-requirements" / "REQ-WP-009.md"
    bad.write_text("---\ntitle: no id here\n---\n\nbody\n")
    with pytest.raises(ValueError, match="REQ-WP-009.md: missing 'id'"):
        collect_requirements(vault.vault)


def test_requirement_id_must_match_its_filename(vault):
    bad = vault.vault / "10-requirements" / "REQ-WP-010.md"
    bad.write_text("---\nid: REQ-WP-999\n---\n\nbody\n")
    with pytest.raises(ValueError, match="id 'REQ-WP-999' does not match filename"):
        collect_requirements(vault.vault)


def test_constraint_requirement_without_hard_gated_field_raises(vault):
    """`hard_gated` defaults to False when the collector merely reads a
    missing key -- that default must never be reached silently for a
    `type: constraint` note, or R5 (the one rule CLAUDE.md calls
    non-waivable) can be escaped just by leaving a line out of the frontmatter.
    """
    bad = vault.vault / "10-requirements" / "REQ-BIAS-099.md"
    bad.write_text(
        "---\nid: REQ-BIAS-099\ntitle: t\ntype: constraint\nstatus: planned\n---\n\nbody\n"
    )
    with pytest.raises(ValueError, match="REQ-BIAS-099.md: type: constraint requires"):
        collect_requirements(vault.vault)


def test_constraint_requirement_with_explicit_hard_gated_false_is_fine(vault):
    """The check is for an *absent* field, not for the value `false` --
    REQ-PRIN-* notes are `type: constraint` with `hard_gated: false` on
    purpose and must keep collecting normally.
    """
    vault.requirement("REQ-PRIN-001", type_="constraint", hard_gated=False)
    nodes, _ = collect_requirements(vault.vault)
    assert nodes[0].attrs["hard_gated"] is False


def test_specs_produce_specifies_edges(vault):
    vault.spec("001-bootstrap", ["REQ-WP-001", "REQ-WP-002"])
    nodes, edges = collect_specs(vault.specs)
    assert nodes[0].id == "SPEC-001-bootstrap"
    assert nodes[0].kind == "spec"
    assert sorted(e.dst for e in edges if e.kind == "SPECIFIES") == ["REQ-WP-001", "REQ-WP-002"]


def test_spec_with_empty_traces_yields_a_node_but_no_edges(vault):
    vault.spec("002-empty", [])
    nodes, edges = collect_specs(vault.specs)
    assert len(nodes) == 1
    assert edges == []


def test_outcomes_produce_records_edges(vault):
    vault.outcome("OUT-2026-09-07-spec-bootstrap", step="spec", records=["REQ-WP-001"])
    nodes, edges = collect_outcomes(vault.vault)
    assert nodes[0].kind == "outcome"
    assert nodes[0].attrs["step"] == "spec"
    assert [(e.src, e.dst, e.kind) for e in edges] == [
        ("OUT-2026-09-07-spec-bootstrap", "REQ-WP-001", "RECORDS")
    ]


def test_decisions_produce_decides_edges(vault):
    vault.decision("ADR-001", ["REQ-WP-001"])
    nodes, edges = collect_decisions(vault.vault)
    assert nodes[0].kind == "decision"
    assert [(e.src, e.dst, e.kind) for e in edges] == [("ADR-001", "REQ-WP-001", "DECIDES")]


def test_code_markers_produce_implements_edges(vault):
    vault.source("channelflow/bars.py", ["REQ-WP-005"])
    nodes, edges = collect_code([vault.root / "src"])
    assert nodes[0].kind == "code"
    assert nodes[0].id == "src/channelflow/bars.py"
    assert [(e.src, e.dst, e.kind) for e in edges] == [
        ("src/channelflow/bars.py", "REQ-WP-005", "IMPLEMENTS")
    ]


def test_a_file_with_two_markers_yields_one_node_and_two_edges(vault):
    vault.source("channelflow/channels.py", ["REQ-WP-006", "REQ-BIAS-002"])
    nodes, edges = collect_code([vault.root / "src"])
    assert len(nodes) == 1
    assert len(edges) == 2


def test_files_without_markers_produce_no_nodes(vault):
    (vault.root / "src" / "plain.py").write_text("def f():\n    return 1\n")
    nodes, edges = collect_code([vault.root / "src"])
    assert nodes == []
    assert edges == []


def test_collect_code_ignores_untracked_files_in_a_git_repo(vault):
    """A local scratch file with a marker must not become a node just
    because it happens to sit under a collected root: it changes the
    committed dashboard for something nobody else can see or reproduce.
    """
    subprocess.run(["git", "init", "-q"], cwd=vault.root, check=True)
    vault.source("channelflow/tracked.py", ["REQ-WP-005"])
    subprocess.run(["git", "add", "src/channelflow/tracked.py"], cwd=vault.root, check=True)
    vault.source("channelflow/scratch.py", ["REQ-WP-006"])  # never added

    nodes, _ = collect_code([vault.root / "src"])

    ids = {n.id for n in nodes}
    assert "src/channelflow/tracked.py" in ids
    assert "src/channelflow/scratch.py" not in ids


def test_collect_code_finds_a_tracked_file_with_a_non_ascii_name(vault):
    """Under git's default core.quotePath=true, plain `ls-files` prints a
    non-ASCII filename as a C-quoted string (e.g. "caf\\303\\251.py"), which
    never matches `(root / line)` -- a tracked file would then be silently
    treated as untracked and its markers would vanish with no diagnostic.
    `_git_tracked_files` must use `-z` so this keeps matching.
    """
    subprocess.run(["git", "init", "-q"], cwd=vault.root, check=True)
    subprocess.run(["git", "config", "core.quotePath", "true"], cwd=vault.root, check=True)
    vault.source("channelflow/café.py", ["REQ-WP-005"])
    subprocess.run(["git", "add", "src/channelflow/café.py"], cwd=vault.root, check=True)

    nodes, _ = collect_code([vault.root / "src"])

    assert {n.id for n in nodes} == {"src/channelflow/café.py"}


def test_collect_code_falls_back_to_unfiltered_outside_a_git_repo(vault):
    """`vault.root` here is a bare tmp_path, not a git repository -- git
    filtering must fail closed (no filtering) rather than crash or find
    nothing.
    """
    vault.source("channelflow/bars.py", ["REQ-WP-005"])
    nodes, _ = collect_code([vault.root / "src"])
    assert {n.id for n in nodes} == {"src/channelflow/bars.py"}


def test_code_collection_skips_pycache(vault):
    cache = vault.root / "src" / "__pycache__"
    cache.mkdir()
    (cache / "stale.py").write_text("# @trace: REQ-WP-001\n")
    nodes, _ = collect_code([vault.root / "src"])
    assert nodes == []


def test_requirement_id_grammar_is_enforced_even_when_filename_matches(vault):
    """id == filename stem is not enough: a malformed id like REQ-WP-001b
    would otherwise slip into the graph as a real node, and no source
    comment could ever correctly reference it (see the TRACE_COMMENT
    anchoring fix below) -- an invisible dead end. Catching it at collection
    time fails loud instead of leaving it silently unlinkable forever.
    """
    bad = vault.vault / "10-requirements" / "REQ-WP-001b.md"
    bad.write_text("---\nid: REQ-WP-001b\n---\n\nbody\n")
    with pytest.raises(ValueError, match="does not match the requirement id grammar"):
        collect_requirements(vault.vault)


def test_trace_comment_with_a_malformed_trailing_letter_matches_nothing(vault):
    """Unanchored, [0-9A-Z]+ would greedily match "001" and stop before the
    lowercase "b", crediting the code to the real, but different,
    REQ-WP-001 -- a silent misattribution to an existing requirement. The
    trailing negative lookahead must make the whole token fail to match
    instead, rather than truncate it.
    """
    vault.source("channelflow/thing.py", ["REQ-WP-001b"])
    nodes, edges = collect_code([vault.root / "src"])
    assert edges == []
    assert nodes == []


def test_requirement_token_with_a_letter_is_not_truncated_to_digits(vault):
    # PRD phases 1A and 7A give requirement tokens that carry a trailing letter
    # (REQ-PHASE-1A, REQ-PHASE-7A); the id must survive intact, not get chopped
    # into a shorter, differently-meaning numeric id.
    vault.source("channelflow/phases.py", ["REQ-PHASE-1A"])
    _, edges = collect_code([vault.root / "src"])
    assert [e.dst for e in edges] == ["REQ-PHASE-1A"]


def test_collect_tests_reads_the_plugin_dump(vault, tmp_path):
    from tools.trace.collect import collect_tests

    dump = tmp_path / "tests.json"
    dump.write_text(
        '[{"nodeid": "tests/unit/test_bars.py::test_close", "requirements": ["REQ-WP-005"]}]'
    )
    nodes, edges = collect_tests(dump)
    assert nodes[0].kind == "test"
    assert nodes[0].path == "tests/unit/test_bars.py"
    assert [(e.src, e.dst, e.kind) for e in edges] == [
        ("tests/unit/test_bars.py::test_close", "REQ-WP-005", "VERIFIES")
    ]


def test_collect_tests_tolerates_a_missing_dump(tmp_path):
    from tools.trace.collect import collect_tests

    nodes, edges = collect_tests(tmp_path / "absent.json")
    assert (nodes, edges) == ([], [])


def test_a_workflow_file_can_carry_a_marker(vault):
    """A gate defined in YAML is an implementation too.

    REQ-INFRA-002 is implemented by `.github/workflows/ci.yml` and nothing
    else. While collection was Python-only, R8 was unsatisfiable for it --
    found when R8 was added and immediately flagged a requirement whose
    implementation was real and simply invisible.
    """
    workflow = vault.root / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text("# @trace: REQ-INFRA-002\nname: CI\n")

    nodes, edges = collect_code([vault.root / ".github"])

    assert [n.id for n in nodes] == [".github/workflows/ci.yml"]
    assert [(e.src, e.dst, e.kind) for e in edges] == [
        (".github/workflows/ci.yml", "REQ-INFRA-002", "IMPLEMENTS")
    ]


def test_frontend_code_can_carry_a_marker(vault):
    """PRD section 37 puts product web code under `apps/web`, and CODE_SUFFIXES
    has always included `.tsx` -- but `apps/` was not a collector root, so a
    marker there could never become an edge.

    Recorded as an open gap by REQ-WP-001 and closed here, because REQ-WP-009's
    implementation is largely TypeScript and R8 would otherwise be
    unsatisfiable for it.
    """
    component = vault.root / "apps" / "web" / "src" / "Chart.tsx"
    component.parent.mkdir(parents=True, exist_ok=True)
    component.write_text("// @trace: REQ-WP-009\nexport const Chart = () => null;\n")

    nodes, edges = collect_code([vault.root / "apps"])

    assert [n.id for n in nodes] == ["apps/web/src/Chart.tsx"]
    assert [(e.src, e.dst, e.kind) for e in edges] == [
        ("apps/web/src/Chart.tsx", "REQ-WP-009", "IMPLEMENTS")
    ]


def test_a_built_bundle_is_not_collected(vault):
    """`dist/` holds compiled output whose markers are copies of the source's.

    Collecting both would double every frontend edge and put a build artifact
    in the traceability graph. It is gitignored today, so the filter is belt
    and braces -- but a repo that ever committed a bundle would silently
    acquire duplicate nodes.
    """
    built = vault.root / "apps" / "web" / "dist" / "assets" / "index-abc123.js"
    built.parent.mkdir(parents=True, exist_ok=True)
    built.write_text("// @trace: REQ-WP-009\nconsole.log(1);\n")

    nodes, _ = collect_code([vault.root / "apps"])

    assert nodes == []


@pytest.fixture
def handed_down_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """What git gives a pre-commit hook: an index file of its own, by absolute path."""
    index = tmp_path.parent / f"{tmp_path.name}-handed-down-index"
    monkeypatch.setenv("GIT_INDEX_FILE", str(index))
    return index


def test_the_vault_fixture_shields_git_from_the_callers_environment(
    handed_down_index: Path, vault
) -> None:
    """A temporary repository must not write into an index its caller handed down.

    `handed_down_index` is listed first, so it has set the variable by the time `vault`
    runs: the test passes only if the fixture removed it. A run in an environment that
    never carried the variable would pass a weaker test and prove nothing.
    """
    assert "GIT_INDEX_FILE" not in os.environ

    subprocess.run(["git", "init", "-q"], cwd=vault.root, check=True)
    vault.source("channelflow/shielded.py", ["REQ-WP-005"])
    subprocess.run(["git", "add", "src/channelflow/shielded.py"], cwd=vault.root, check=True)

    assert not handed_down_index.exists(), "git add wrote into the caller's index"
    assert (vault.root / ".git" / "index").exists()
