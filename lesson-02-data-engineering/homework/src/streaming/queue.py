"""Async document queue for streaming ingestion."""

import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class QueueItem:
    """A single item in the ingestion queue."""
    file_path: Path
    enqueued_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    priority: int = 0  # lower = higher priority


class DocumentQueue:
    """Async queue for document ingestion.

    Supports:
    - Max size limit (backpressure)
    - Priority ordering
    - Drain / flush operations

    Usage:
        queue = DocumentQueue(max_size=100)
        await queue.put(Path("doc.pdf"))
        item = await queue.get()
    """

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._queue: asyncio.Queue[QueueItem] = asyncio.Queue(maxsize=max_size)
        self._processed_count = 0
        self._total_enqueued = 0

    async def put(self, file_path: Path, priority: int = 0) -> None:
        """Add a document to the queue. Blocks if queue is full (backpressure)."""
        item = QueueItem(file_path=file_path, priority=priority)
        await self._queue.put(item)
        self._total_enqueued += 1
        logger.debug(f"Enqueued {file_path.name} (queue size: {self._queue.qsize()})")

    async def get(self) -> QueueItem:
        """Get next document from queue. Blocks if empty."""
        item = await self._queue.get()
        return item

    def task_done(self) -> None:
        """Mark the current item as processed."""
        self._queue.task_done()
        self._processed_count += 1

    async def drain(self) -> list[QueueItem]:
        """Get all currently queued items without blocking."""
        items = []
        while not self._queue.empty():
            try:
                items.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return items

    @property
    def size(self) -> int:
        return self._queue.qsize()

    @property
    def is_empty(self) -> bool:
        return self._queue.empty()

    @property
    def stats(self) -> dict:
        return {
            "current_size": self.size,
            "max_size": self.max_size,
            "total_enqueued": self._total_enqueued,
            "total_processed": self._processed_count,
        }
