import json


def test_dump_records_marked_tests(pytester):
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

    # Collection only: the exit code is not what this test asserts.
    pytester.runpytest(
        "-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "--collect-only", "-q"
    )

    entries = json.loads(dump.read_text())
    by_id = {e["nodeid"].split("::")[-1]: e["requirements"] for e in entries}
    assert by_id == {
        "test_one": ["REQ-WP-001"],
        "test_two": ["REQ-WP-002", "REQ-BIAS-003"],
    }


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

    pytester.runpytest(
        "-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "--collect-only", "-q"
    )

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

    pytester.runpytest("-p", "tools.trace.pytest_plugin", "--collect-only", "-q")

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

    pytester.runpytest(
        "-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "--collect-only", "-q"
    )

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

    pytester.runpytest(
        "-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "--collect-only", "-q"
    )

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

    pytester.runpytest(
        "-p", "tools.trace.pytest_plugin", f"--trace-dump={dump}", "--collect-only", "-q"
    )

    entries = json.loads(dump.read_text())
    nodeids = [e["nodeid"] for e in entries]
    assert nodeids == sorted(nodeids)
    assert [n.split("::")[-1] for n in nodeids] == ["test_a", "test_b", "test_c"]
