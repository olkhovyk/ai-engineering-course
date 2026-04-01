"""Data versioning — hash-based snapshots for reproducibility.

Every time the pipeline processes a batch of documents, a version snapshot
is created containing:
- Content hash (SHA256) for integrity verification
- Timestamp
- Metadata (file list, counts)
- The processed data itself

This lets you:
- Reproduce any past dataset state
- Compare versions (what changed?)
- Roll back to a known-good snapshot
"""

import hashlib
import json
import logging
from datetime import datetime, UTC
from pathlib import Path

logger = logging.getLogger(__name__)


class VersionStore:
    """Manages versioned snapshots of processed data.

    Usage:
        store = VersionStore("data/versions")
        vid = store.create_snapshot(data, "initial ingestion")
        snapshot = store.get_snapshot(vid)
        store.list_versions()
    """

    def __init__(self, versions_dir: str | Path = "data/versions", max_versions: int = 10):
        self.versions_dir = Path(versions_dir)
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.max_versions = max_versions
        self._manifest_path = self.versions_dir / "manifest.json"

    def create_snapshot(self, data: list[dict] | dict, description: str = "") -> str:
        """Create a new version snapshot. Returns the version ID."""
        # Serialize data deterministically for hashing
        serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
        content_hash = hashlib.sha256(serialized.encode()).hexdigest()[:12]
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        version_id = f"v_{timestamp}_{content_hash}"

        # Save snapshot
        snapshot = {
            "version_id": version_id,
            "created_at": datetime.now(UTC).isoformat(),
            "content_hash": content_hash,
            "description": description,
            "doc_count": len(data) if isinstance(data, list) else 1,
            "data": data,
        }

        snapshot_path = self.versions_dir / f"{version_id}.json"
        snapshot_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))

        # Update manifest
        self._update_manifest(version_id, description, content_hash)

        # Prune old versions
        self._prune_old_versions()

        logger.info(f"Created snapshot {version_id} ({description})")
        return version_id

    def get_snapshot(self, version_id: str) -> dict | None:
        """Load a specific version snapshot."""
        path = self.versions_dir / f"{version_id}.json"
        if not path.exists():
            logger.warning(f"Snapshot {version_id} not found")
            return None
        return json.loads(path.read_text())

    def list_versions(self) -> list[dict]:
        """List all version snapshots (without data)."""
        manifest = self._load_manifest()
        return manifest.get("versions", [])

    def compare_versions(self, v1_id: str, v2_id: str) -> dict:
        """Compare two snapshots — show what changed."""
        s1 = self.get_snapshot(v1_id)
        s2 = self.get_snapshot(v2_id)

        if not s1 or not s2:
            return {"error": "One or both snapshots not found"}

        s1_sources = {d.get("source", "") for d in s1.get("data", []) if isinstance(d, dict)}
        s2_sources = {d.get("source", "") for d in s2.get("data", []) if isinstance(d, dict)}

        return {
            "v1": v1_id,
            "v2": v2_id,
            "same_hash": s1["content_hash"] == s2["content_hash"],
            "v1_doc_count": s1["doc_count"],
            "v2_doc_count": s2["doc_count"],
            "added": list(s2_sources - s1_sources),
            "removed": list(s1_sources - s2_sources),
            "common": list(s1_sources & s2_sources),
        }

    def _update_manifest(self, version_id: str, description: str, content_hash: str):
        manifest = self._load_manifest()
        manifest.setdefault("versions", []).append({
            "version_id": version_id,
            "created_at": datetime.now(UTC).isoformat(),
            "content_hash": content_hash,
            "description": description,
        })
        self._manifest_path.write_text(json.dumps(manifest, indent=2))

    def _load_manifest(self) -> dict:
        if self._manifest_path.exists():
            return json.loads(self._manifest_path.read_text())
        return {"versions": []}

    def _prune_old_versions(self):
        """Remove oldest snapshots if we exceed max_versions."""
        manifest = self._load_manifest()
        versions = manifest.get("versions", [])
        if len(versions) <= self.max_versions:
            return

        to_remove = versions[:-self.max_versions]
        for v in to_remove:
            path = self.versions_dir / f"{v['version_id']}.json"
            if path.exists():
                path.unlink()
                logger.info(f"Pruned old snapshot: {v['version_id']}")

        manifest["versions"] = versions[-self.max_versions:]
        self._manifest_path.write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    import sys

    store = VersionStore("data/versions")
    if "--list" in sys.argv:
        versions = store.list_versions()
        if not versions:
            print("No versions found.")
        for v in versions:
            print(f"  {v['version_id']}  |  {v['created_at']}  |  {v['description']}")
    else:
        print("Usage: python version_store.py --list")
