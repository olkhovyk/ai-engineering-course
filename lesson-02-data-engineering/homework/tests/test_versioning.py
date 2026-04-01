"""Tests for the data versioning store."""

import pytest
from src.versioning.version_store import VersionStore


@pytest.fixture
def store(tmp_path):
    return VersionStore(versions_dir=tmp_path / "versions", max_versions=3)


def test_create_snapshot(store):
    data = [{"source": "doc1.pdf", "text": "hello"}]
    vid = store.create_snapshot(data, "test snapshot")

    assert vid.startswith("v_")
    assert "test snapshot" in str(store.list_versions())


def test_get_snapshot(store):
    data = [{"source": "doc1.pdf", "text": "hello"}]
    vid = store.create_snapshot(data, "get test")

    snapshot = store.get_snapshot(vid)
    assert snapshot is not None
    assert snapshot["version_id"] == vid
    assert snapshot["data"] == data
    assert snapshot["doc_count"] == 1


def test_get_nonexistent_snapshot(store):
    assert store.get_snapshot("v_nonexistent_abc123") is None


def test_list_versions(store):
    store.create_snapshot([{"a": 1}], "first")
    store.create_snapshot([{"b": 2}], "second")

    versions = store.list_versions()
    assert len(versions) == 2
    descriptions = [v["description"] for v in versions]
    assert "first" in descriptions
    assert "second" in descriptions


def test_compare_versions(store):
    v1 = store.create_snapshot(
        [{"source": "a.pdf"}, {"source": "b.pdf"}], "v1"
    )
    v2 = store.create_snapshot(
        [{"source": "b.pdf"}, {"source": "c.pdf"}], "v2"
    )

    diff = store.compare_versions(v1, v2)
    assert diff["v1_doc_count"] == 2
    assert diff["v2_doc_count"] == 2
    assert "a.pdf" in diff["removed"]
    assert "c.pdf" in diff["added"]
    assert "b.pdf" in diff["common"]


def test_same_data_same_hash(store):
    data = [{"source": "doc.pdf", "text": "same content"}]
    v1 = store.create_snapshot(data, "first")
    v2 = store.create_snapshot(data, "second")

    s1 = store.get_snapshot(v1)
    s2 = store.get_snapshot(v2)
    assert s1["content_hash"] == s2["content_hash"]


def test_prune_old_versions(store):
    """Store has max_versions=3, so creating 5 should prune the first 2."""
    vids = []
    for i in range(5):
        vid = store.create_snapshot([{"i": i}], f"snapshot {i}")
        vids.append(vid)

    versions = store.list_versions()
    assert len(versions) == 3

    # Oldest should be pruned
    assert store.get_snapshot(vids[0]) is None
    assert store.get_snapshot(vids[1]) is None
    # Newest should exist
    assert store.get_snapshot(vids[4]) is not None
