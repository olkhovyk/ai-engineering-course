"""Parsed document data model for the ingestion pipeline."""

from dataclasses import dataclass, field
from datetime import datetime, UTC


@dataclass
class ParsedDocument:
    """Result of parsing a single document."""

    source_path: str
    file_type: str
    text: str
    metadata: dict = field(default_factory=dict)
    ocr_applied: bool = False
    parsed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    char_count: int = 0

    def __post_init__(self):
        self.char_count = len(self.text)
