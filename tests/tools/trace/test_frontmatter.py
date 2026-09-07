import pytest

from tools.trace.frontmatter import split_frontmatter

NOTE = """---
id: REQ-US-001
status: draft
depends_on: [REQ-WP-003]
---

## Requirement

Scan markets.
"""


def test_splits_metadata_from_body():
    meta, body = split_frontmatter(NOTE)
    assert meta["id"] == "REQ-US-001"
    assert meta["depends_on"] == ["REQ-WP-003"]
    assert body.startswith("\n## Requirement")


def test_missing_frontmatter_yields_empty_metadata():
    meta, body = split_frontmatter("# Just a heading\n")
    assert meta == {}
    assert body == "# Just a heading\n"


def test_unterminated_frontmatter_is_not_metadata():
    meta, body = split_frontmatter("---\nid: REQ-US-001\nno closing fence\n")
    assert meta == {}
    assert body.startswith("---")


def test_empty_frontmatter_block_yields_empty_metadata():
    meta, body = split_frontmatter("---\n---\nbody\n")
    assert meta == {}
    assert body == "body\n"


def test_malformed_yaml_raises_with_the_offending_text():
    with pytest.raises(ValueError, match="invalid YAML frontmatter"):
        split_frontmatter("---\nid: [unclosed\n---\nbody\n")


def test_non_mapping_frontmatter_raises():
    with pytest.raises(ValueError, match="frontmatter must be a mapping"):
        split_frontmatter("---\n- a\n- b\n---\nbody\n")


def test_leading_blank_lines_before_the_fence_are_tolerated():
    meta, _ = split_frontmatter("\n\n---\nid: REQ-US-002\n---\nbody\n")
    assert meta["id"] == "REQ-US-002"
