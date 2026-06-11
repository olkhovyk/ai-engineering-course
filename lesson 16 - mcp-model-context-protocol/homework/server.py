from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("notes-server")

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_NOTES_PATH = BASE_DIR / "data" / "notes.json"
NOTES_PATH = Path(os.getenv("NOTES_DB_PATH", DEFAULT_NOTES_PATH))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_storage() -> None:
    NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not NOTES_PATH.exists():
        NOTES_PATH.write_text("[]", encoding="utf-8")


def _load_notes() -> list[dict[str, Any]]:
    _ensure_storage()
    raw = NOTES_PATH.read_text(encoding="utf-8")
    if not raw.strip():
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError(f"Notes storage must contain a JSON array: {NOTES_PATH}")
    return data


def _save_notes(notes: list[dict[str, Any]]) -> None:
    _ensure_storage()
    NOTES_PATH.write_text(
        json.dumps(notes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _normalize_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    return sorted({tag.strip().lower() for tag in tags if tag.strip()})


@mcp.tool()
def add_note(title: str, content: str, tags: list[str] | None = None) -> dict[str, Any]:
    """Add a note to the local notes database."""
    clean_title = title.strip()
    clean_content = content.strip()
    if not clean_title:
        raise ValueError("title must not be empty")
    if not clean_content:
        raise ValueError("content must not be empty")

    notes = _load_notes()
    note = {
        "id": str(uuid4()),
        "title": clean_title,
        "content": clean_content,
        "tags": _normalize_tags(tags),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    notes.append(note)
    _save_notes(notes)
    return note


@mcp.tool()
def search_notes(query: str, tag: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    """Search notes by text query and optional tag."""
    clean_query = query.strip().lower()
    clean_tag = tag.strip().lower() if tag else None
    safe_limit = max(1, min(limit, 50))

    if not clean_query and not clean_tag:
        raise ValueError("query or tag must be provided")

    matches: list[dict[str, Any]] = []
    for note in _load_notes():
        haystack = f"{note.get('title', '')} {note.get('content', '')}".lower()
        tags = note.get("tags", [])
        text_matches = not clean_query or clean_query in haystack
        tag_matches = not clean_tag or clean_tag in tags
        if text_matches and tag_matches:
            matches.append(note)

    return matches[:safe_limit]


@mcp.tool()
def list_notes(limit: int = 10) -> list[dict[str, Any]]:
    """List the newest notes from the local notes database."""
    safe_limit = max(1, min(limit, 50))
    notes = _load_notes()
    return list(reversed(notes))[:safe_limit]


@mcp.resource("notes://all")
def all_notes() -> str:
    """Return all stored notes as JSON."""
    return json.dumps(_load_notes(), ensure_ascii=False, indent=2)


@mcp.resource("notes://stats")
def notes_stats() -> str:
    """Return basic statistics about stored notes."""
    notes = _load_notes()
    tags: dict[str, int] = {}
    for note in notes:
        for tag in note.get("tags", []):
            tags[tag] = tags.get(tag, 0) + 1

    stats = {
        "notes_count": len(notes),
        "tags": tags,
        "storage_path": str(NOTES_PATH),
    }
    return json.dumps(stats, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
