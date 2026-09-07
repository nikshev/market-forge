import json

import pytest


def test_dump_records_marked_tests_that_pass(pytester):
    pytester.makepyfile(
        test_sample="""
        import pytest

        @pytest.mark.trace("REQ-WP-001")
        def test_one():
            pass

        @pytest.mark.trace("REQ-WP-002", "REQ-BIAS-003")
        def test_two():
            pass

        def test_unmarked():
            pass
        """
    )
    pytester.makeini(
        "[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n"
    )
    dump = pytester.path / "out" / "tests.json"

    # A real run, not --collect-only: both marked tests genuinely pass, so
    # both are entitled to a VERIFIES edge.
    result = pytester.runpytest("-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "-q")
    result.assert_outcomes(passed=3)

    entries = json.loads(dump.read_text())
    by_id = {e["nodeid"].split("::")[-1]: e["requirements"] for e in entries}
    assert by_id == {
        "test_one": ["REQ-WP-001"],
        "test_two": ["REQ-WP-002", "REQ-BIAS-003"],
    }


@pytest.mark.trace("REQ-INFRA-001")
def test_parametrized_tests_are_recorded_once_per_case(pytester):
    pytester.makepyfile(
        test_param="""
        import pytest

        @pytest.mark.trace("REQ-WP-004")
        @pytest.mark.parametrize("value", [1, 2, 3])
        def test_each(value):
            pass
        """
    )
    pytester.makeini(
        "[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n"
    )
    dump = pytester.path / "tests.json"

    pytester.runpytest("-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "-q")

    entries = json.loads(dump.read_text())
    assert len(entries) == 3
    assert all(e["requirements"] == ["REQ-WP-004"] for e in entries)


def test_no_dump_option_writes_nothing(pytester):
    pytester.makepyfile(
        test_quiet="""
        import pytest

        @pytest.mark.trace("REQ-WP-001")
        def test_one():
            pass
        """
    )
    pytester.makeini(
        "[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n"
    )

    pytester.runpytest("-p", "tools.trace.pytest_plugin", "-q")

    assert not (pytester.path / "tests.json").exists()


def test_dump_creates_missing_parent_directories(pytester):
    pytester.makepyfile(
        test_deep="""
        import pytest

        @pytest.mark.trace("REQ-WP-001")
        def test_one():
            pass
        """
    )
    pytester.makeini(
        "[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n"
    )
    dump = pytester.path / "a" / "b" / "tests.json"

    pytester.runpytest("-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "-q")

    assert dump.is_file()


def test_repeated_ids_on_one_test_are_deduplicated_in_order(pytester):
    pytester.makepyfile(
        test_dupe="""
        import pytest

        @pytest.mark.trace("REQ-WP-001", "REQ-BIAS-002", "REQ-WP-001")
        def test_one():
            pass
        """
    )
    pytester.makeini(
        "[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n"
    )
    dump = pytester.path / "tests.json"

    pytester.runpytest("-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "-q")

    entries = json.loads(dump.read_text())
    assert len(entries) == 1
    assert entries[0]["requirements"] == ["REQ-WP-001", "REQ-BIAS-002"]


def test_entries_are_sorted_by_nodeid_regardless_of_definition_order(pytester):
    # Defined as test_c, test_a, test_b: pytest collects in definition order,
    # so the unsorted collection order is [test_c, test_a, test_b] here, which
    # differs from the alphabetically sorted order this test asserts on. If
    # the functions were named in alphabetical order already, collection order
    # and sorted order would coincide and this guard would prove nothing.
    pytester.makepyfile(
        test_unsorted="""
        import pytest

        @pytest.mark.trace("REQ-WP-003")
        def test_c():
            pass

        @pytest.mark.trace("REQ-WP-001")
        def test_a():
            pass

        @pytest.mark.trace("REQ-WP-002")
        def test_b():
            pass
        """
    )
    pytester.makeini(
        "[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n"
    )
    dump = pytester.path / "tests.json"

    pytester.runpytest("-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "-q")

    entries = json.loads(dump.read_text())
    nodeids = [e["nodeid"] for e in entries]
    assert nodeids == sorted(nodeids)
    assert [n.split("::")[-1] for n in nodeids] == ["test_a", "test_b", "test_c"]


# --- CRITICAL 2: a VERIFIES edge means "passed", not "collected" ---


def test_collect_only_writes_no_entries_because_no_outcome_is_knowable(pytester):
    """Under --collect-only nothing has run, so nothing can be said to have
    passed. Rather than guess (or worse, claim every collected+marked test
    verifies its requirement, which is the bug this plugin exists to close),
    the dump is written empty. `make markers` no longer uses --collect-only
    for this exact reason; this test documents the mode's meaning for anyone
    who still invokes it directly.
    """
    pytester.makepyfile(
        test_sample="""
        import pytest

        @pytest.mark.trace("REQ-WP-001")
        def test_one():
            pass
        """
    )
    pytester.makeini(
        "[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n"
    )
    dump = pytester.path / "tests.json"

    pytester.runpytest(
        "-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "--collect-only", "-q"
    )

    assert json.loads(dump.read_text()) == []


def test_skipped_test_produces_no_entry(pytester):
    pytester.makepyfile(
        test_sample="""
        import pytest

        @pytest.mark.trace("REQ-WP-001")
        @pytest.mark.skip(reason="not implemented yet")
        def test_one():
            assert False
        """
    )
    pytester.makeini(
        "[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n"
    )
    dump = pytester.path / "tests.json"

    result = pytester.runpytest("-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "-q")
    result.assert_outcomes(skipped=1)

    assert json.loads(dump.read_text()) == []


def test_xfailed_test_produces_no_entry(pytester):
    pytester.makepyfile(
        test_sample="""
        import pytest

        @pytest.mark.trace("REQ-WP-001")
        @pytest.mark.xfail(reason="known broken")
        def test_one():
            assert False
        """
    )
    pytester.makeini(
        "[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n"
    )
    dump = pytester.path / "tests.json"

    result = pytester.runpytest("-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "-q")
    result.assert_outcomes(xfailed=1)

    assert json.loads(dump.read_text()) == []


def test_xpassed_test_produces_no_entry(pytester):
    """An xfail marker that turns out to pass is still not a plain pass —
    it is flagged (xpass), which is precisely the kind of surprising result a
    VERIFIES edge must not paper over.
    """
    pytester.makepyfile(
        test_sample="""
        import pytest

        @pytest.mark.trace("REQ-WP-001")
        @pytest.mark.xfail(reason="expected to fail, but doesn't")
        def test_one():
            assert True
        """
    )
    pytester.makeini(
        "[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n"
    )
    dump = pytester.path / "tests.json"

    result = pytester.runpytest("-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "-q")
    result.assert_outcomes(xpassed=1)

    assert json.loads(dump.read_text()) == []


def test_failed_test_produces_no_entry_but_a_passing_sibling_still_does(pytester):
    pytester.makepyfile(
        test_sample="""
        import pytest

        @pytest.mark.trace("REQ-WP-001")
        def test_fails():
            assert False

        @pytest.mark.trace("REQ-WP-002")
        def test_passes():
            assert True
        """
    )
    pytester.makeini(
        "[pytest]\nmarkers =\n    trace(*requirement_ids): link a test to requirements\n"
    )
    dump = pytester.path / "tests.json"

    result = pytester.runpytest("-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "-q")
    result.assert_outcomes(passed=1, failed=1)

    entries = json.loads(dump.read_text())
    assert [e["nodeid"].split("::")[-1] for e in entries] == ["test_passes"]
