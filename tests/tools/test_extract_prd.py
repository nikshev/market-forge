from pathlib import Path

import pytest

from tools.extract_prd import extract, write_notes

PRD = Path(__file__).resolve().parents[2] / "channel_flow_prd_codex_ua_v5.md"


@pytest.fixture(scope="module")
def requirements():
    return extract(PRD)


def test_extracts_the_expected_counts(requirements):
    counts: dict[str, int] = {}
    for req in requirements:
        counts[req.id.split("-")[1]] = counts.get(req.id.split("-")[1], 0) + 1
    assert counts == {
        "US": 7,
        "WP": 20,
        "EXP": 17,
        "PHASE": 11,
        "NRT": 6,
        "BIAS": 11,
        "PRIN": 14,
    }
    assert len(requirements) == 86


def test_ids_are_unique(requirements):
    ids = [r.id for r in requirements]
    assert len(ids) == len(set(ids))


def test_phase_ids_keep_their_letter_suffix(requirements):
    phase_ids = {r.id for r in requirements if r.id.startswith("REQ-PHASE-")}
    assert "REQ-PHASE-1A" in phase_ids
    assert "REQ-PHASE-7A" in phase_ids
    assert "REQ-PHASE-0" in phase_ids


def test_constraints_are_typed_as_constraints(requirements):
    for req in requirements:
        kind = req.id.split("-")[1]
        if kind in {"NRT", "BIAS", "PRIN"}:
            assert req.type == "constraint", req.id


def test_hard_gated_is_scoped_to_nrt_and_bias_not_prin(requirements):
    """R5 (never-waivable, correctness constraints need a test) is scoped by
    design to PRD §13A.28 (NRT) and §41 (BIAS), not to every `type:
    constraint` note: the §0 principles (PRIN) include process instructions
    like "implement incrementally" that can never have a test.
    """
    by_kind: dict[str, set[bool]] = {}
    for req in requirements:
        kind = req.id.split("-")[1]
        by_kind.setdefault(kind, set()).add(req.hard_gated)
    assert by_kind["NRT"] == {True}
    assert by_kind["BIAS"] == {True}
    assert by_kind["PRIN"] == {False}
    for kind in ("US", "WP", "EXP", "PHASE"):
        assert by_kind[kind] == {False}


def test_written_note_carries_the_hard_gated_flag(requirements, tmp_path):
    bias001 = _by_id(requirements, "REQ-BIAS-001")
    prin001 = _by_id(requirements, "REQ-PRIN-001")
    vault_dir = tmp_path / "vault"
    (vault_dir / "10-requirements").mkdir(parents=True)
    written = write_notes([bias001, prin001], vault_dir)
    texts = {path.stem: path.read_text() for path in written}
    assert "hard_gated: true" in texts["REQ-BIAS-001"]
    assert "hard_gated: false" in texts["REQ-PRIN-001"]


def test_every_requirement_carries_a_prd_reference(requirements):
    for req in requirements:
        assert req.prd_ref, req.id
        assert req.prd_lines, req.id


def test_written_notes_are_collectable(requirements, tmp_path):
    from tools.trace.collect import collect_requirements

    vault_dir = tmp_path / "vault"
    (vault_dir / "10-requirements").mkdir(parents=True)
    written = write_notes(requirements, vault_dir)
    assert len(written) == 86

    nodes, edges = collect_requirements(vault_dir)
    assert len(nodes) == 86
    assert all(n.attrs["status"] == "draft" for n in nodes)


def test_written_notes_carry_trace_markers(requirements, tmp_path):
    vault_dir = tmp_path / "vault"
    (vault_dir / "10-requirements").mkdir(parents=True)
    written = write_notes(requirements[:1], vault_dir)
    text = written[0].read_text()
    assert "<!-- trace:begin -->" in text
    assert "<!-- trace:end -->" in text


def test_write_notes_refuses_to_clobber_an_existing_note(requirements, tmp_path):
    vault_dir = tmp_path / "vault"
    (vault_dir / "10-requirements").mkdir(parents=True)
    write_notes(requirements[:1], vault_dir)
    with pytest.raises(FileExistsError):
        write_notes(requirements[:1], vault_dir)


# --- Acceptance extraction (task-11a addition) -----------------------------


def _by_id(requirements, req_id):
    matches = [r for r in requirements if r.id == req_id]
    assert matches, f"{req_id} not found"
    return matches[0]


def test_phase_acceptance_is_extracted_from_the_acceptance_cue(requirements):
    phase0 = _by_id(requirements, "REQ-PHASE-0")
    assert "`make test` green" in phase0.acceptance
    assert "services boot locally" in phase0.acceptance
    assert "canonical event serialization roundtrip" in phase0.acceptance
    # The Deliverables: block that precedes Acceptance: must not leak in.
    assert "repo layout" not in phase0.acceptance


def test_work_package_acceptance_is_extracted_from_the_done_when_cue(requirements):
    wp001 = _by_id(requirements, "REQ-WP-001")
    assert "one command starts dev stack" in wp001.acceptance
    # The Tasks: block that precedes Done when: must not leak in.
    assert "create pyproject" not in wp001.acceptance


def test_constraint_acceptance_is_the_rule_statement_itself(requirements):
    bias001 = _by_id(requirements, "REQ-BIAS-001")
    assert bias001.acceptance == bias001.title
    assert bias001.acceptance == "No random train/test primary split."


def test_section_with_no_cue_leaves_acceptance_empty(requirements):
    us001 = _by_id(requirements, "REQ-US-001")
    assert us001.acceptance == ""


def test_written_note_for_a_no_cue_section_carries_the_marker_line(requirements, tmp_path):
    us001 = _by_id(requirements, "REQ-US-001")
    vault_dir = tmp_path / "vault"
    (vault_dir / "10-requirements").mkdir(parents=True)
    [path] = write_notes([us001], vault_dir)
    text = path.read_text()
    assert "no explicit acceptance criteria" in text
    assert "ACCEPTANCE-NOT-SPECIFIED" in text
    assert "draft" in text.split("## Acceptance")[1].split("## Trace")[0]


# A "Deliverables:" block is a list of things to build, not a criterion for
# knowing they work, so it must never be selected as the acceptance source on
# its own -- even though it is one of the cue lines the extractor recognizes
# as a section boundary. Phases 5, 6 and 8 are the entire population of
# phases that carry Deliverables: and no Acceptance:/Done when:/Metric(s):,
# so all three are checked, not just one.
@pytest.mark.parametrize("phase_id", ["REQ-PHASE-5", "REQ-PHASE-6", "REQ-PHASE-8"])
def test_deliverables_only_section_does_not_become_acceptance(requirements, tmp_path, phase_id):
    phase = _by_id(requirements, phase_id)
    assert phase.acceptance == ""

    vault_dir = tmp_path / "vault"
    (vault_dir / "10-requirements").mkdir(parents=True)
    [path] = write_notes([phase], vault_dir)
    text = path.read_text()
    assert "ACCEPTANCE-NOT-SPECIFIED" in text

    acceptance_section = text.split("## Acceptance")[1].split("## Trace")[0]
    deliverables_section = text.split("## Requirement")[1].split("## Acceptance")[0]
    # The Deliverables bullets belong to ## Requirement (the frozen PRD
    # excerpt) and must not leak into ## Acceptance.
    for bullet in deliverables_section.strip().splitlines()[1:]:
        bullet = bullet.strip()
        if bullet:
            assert bullet not in acceptance_section
