"""Batching logic — collects items and flushes by size or timeout."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Callable, Awaitable

from .queue import DocumentQueue, QueueItem

logger = logging.getLogger(__name__)


class Batcher:
    """Collects documents from a queue and flushes them in batches.

    Flush triggers:
    1. Batch reaches `batch_size` items
    2. `timeout_sec` seconds elapsed since first item in current batch

    This is a core streaming ingestion pattern — it balances throughput
    (processing many docs at once) with latency (not waiting too long).

    Usage:
        batcher = Batcher(queue, batch_size=5, timeout_sec=10)
        batcher.on_batch(process_batch)  # register callback
        await batcher.run()              # start consuming
    """

    def __init__(self, queue: DocumentQueue, batch_size: int = 5,
                 timeout_sec: float = 10.0):
        self.queue = queue
        self.batch_size = batch_size
        self.timeout_sec = timeout_sec
        self._batch: list[QueueItem] = []
        self._batch_start: float | None = None
        self._callback: Callable[[list[QueueItem]], Awaitable[None]] | None = None
        self._running = False
        self._batches_flushed = 0

    def on_batch(self, callback: Callable[[list[QueueItem]], Awaitable[None]]) -> None:
        """Register a callback that will be called with each batch."""
        self._callback = callback

    async def run(self) -> None:
        """Start consuming from the queue and flushing batches."""
        if not self._callback:
            raise RuntimeError("No batch callback registered. Call on_batch() first.")

        self._running = True
        logger.info(f"Batcher started (batch_size={self.batch_size}, timeout={self.timeout_sec}s)")

        while self._running:
            try:
                # Wait for next item with timeout
                remaining_timeout = self._time_until_flush()
                item = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=remaining_timeout
                )
                self._add_to_batch(item)
                self.queue.task_done()

                # Flush if batch is full
                if len(self._batch) >= self.batch_size:
                    await self._flush("batch_size_reached")

            except asyncio.TimeoutError:
                # Timeout elapsed — flush whatever we have
                if self._batch:
                    await self._flush("timeout")

            except asyncio.CancelledError:
                # Graceful shutdown — flush remaining
                if self._batch:
                    await self._flush("shutdown")
                break

    def stop(self) -> None:
        """Signal the batcher to stop after current batch."""
        self._running = False

    def _add_to_batch(self, item: QueueItem) -> None:
        if not self._batch:
            self._batch_start = time.monotonic()
        self._batch.append(item)

    def _time_until_flush(self) -> float:
        """How many seconds until timeout-based flush."""
        if self._batch_start is None:
            return self.timeout_sec
        elapsed = time.monotonic() - self._batch_start
        return max(0.1, self.timeout_sec - elapsed)

    async def _flush(self, reason: str) -> None:
        """Send current batch to callback and reset."""
        batch = self._batch
        self._batch = []
        self._batch_start = None
        self._batches_flushed += 1

        logger.info(f"Flushing batch #{self._batches_flushed} ({len(batch)} items, reason={reason})")
        await self._callback(batch)

    @property
    def stats(self) -> dict:
        return {
            "batches_flushed": self._batches_flushed,
            "current_batch_size": len(self._batch),
            "batch_size_limit": self.batch_size,
            "timeout_sec": self.timeout_sec,
        }
