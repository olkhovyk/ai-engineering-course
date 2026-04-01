"""Text chunking using langchain text splitters.

Replaces hand-rolled chunking with RecursiveCharacterTextSplitter,
which tries to split on semantically meaningful boundaries
(paragraphs → sentences → words → characters).
"""

import logging
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A single text chunk with position info."""
    text: str
    index: int
    start_char: int
    end_char: int

    @property
    def char_count(self) -> int:
        return len(self.text)


# Each strategy uses different separator priority
STRATEGY_SEPARATORS = {
    "fixed_size": ["\n\n", "\n", " ", ""],
    "sentence": [". ", "! ", "? ", "\n\n", "\n", " ", ""],
    "paragraph": ["\n\n", "\n", ". ", " ", ""],
}


class Chunker:
    """Splits text into chunks using langchain's RecursiveCharacterTextSplitter.

    Strategies:
    - fixed_size: split by size, prefer natural boundaries
    - sentence: split on sentence boundaries first
    - paragraph: split on paragraph boundaries first
    """

    def __init__(self, strategy: str = "fixed_size", chunk_size: int = 512,
                 chunk_overlap: int = 50):
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        if strategy not in STRATEGY_SEPARATORS:
            raise ValueError(
                f"Unknown strategy '{strategy}'. "
                f"Use: {list(STRATEGY_SEPARATORS.keys())}"
            )

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=STRATEGY_SEPARATORS[strategy],
        )

    def chunk(self, text: str) -> list[Chunk]:
        """Split text into chunks."""
        if not text.strip():
            return []

        raw_chunks = self._splitter.split_text(text)

        # Build Chunk objects with position tracking
        chunks = []
        offset = 0
        for idx, chunk_text in enumerate(raw_chunks):
            start = text.find(chunk_text, offset)
            if start == -1:
                start = offset
            end = start + len(chunk_text)
            chunks.append(Chunk(
                text=chunk_text, index=idx,
                start_char=start, end_char=end,
            ))
            offset = max(offset, start + 1)

        logger.info(
            f"Chunked text ({len(text)} chars) into {len(chunks)} chunks "
            f"(strategy={self.strategy})"
        )
        return chunks
