"""File system watcher — detects new documents and enqueues them."""

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".html", ".htm", ".xlsx", ".xls"}


class FileWatcher:
    """Watches a directory for new files and pushes them to a queue.

    Uses the `watchdog` library for OS-level file system events.
    Falls back to polling if watchdog is unavailable.

    Usage:
        watcher = FileWatcher("data/raw", queue)
        await watcher.start()   # blocks, watching for changes
    """

    def __init__(self, watch_dir: str | Path, queue, poll_interval: float = 2.0):
        self.watch_dir = Path(watch_dir)
        self.queue = queue
        self.poll_interval = poll_interval
        self._seen: set[str] = set()
        self._running = False

    async def start(self) -> None:
        """Start watching. Tries watchdog first, falls back to polling."""
        self._running = True
        self.watch_dir.mkdir(parents=True, exist_ok=True)

        # Index existing files so we don't re-process them
        for f in self._scan_dir():
            self._seen.add(str(f))

        logger.info(f"Watching {self.watch_dir} (found {len(self._seen)} existing files)")

        try:
            await self._watch_with_watchdog()
        except ImportError:
            logger.info("watchdog not installed, falling back to polling")
            await self._watch_with_polling()

    async def _watch_with_watchdog(self) -> None:
        """Use watchdog library for efficient file system monitoring."""
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        loop = asyncio.get_event_loop()

        class Handler(FileSystemEventHandler):
            def __init__(self, watcher_instance):
                self.watcher = watcher_instance

            def on_created(self, event):
                if not event.is_directory:
                    path = Path(event.src_path)
                    if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                        if str(path) not in self.watcher._seen:
                            self.watcher._seen.add(str(path))
                            asyncio.run_coroutine_threadsafe(
                                self.watcher.queue.put(path), loop
                            )
                            logger.info(f"Detected new file: {path.name}")

        observer = Observer()
        observer.schedule(Handler(self), str(self.watch_dir), recursive=False)
        observer.start()

        try:
            while self._running:
                await asyncio.sleep(1)
        finally:
            observer.stop()
            observer.join()

    async def _watch_with_polling(self) -> None:
        """Fallback: periodically scan directory for new files."""
        while self._running:
            for file_path in self._scan_dir():
                key = str(file_path)
                if key not in self._seen:
                    self._seen.add(key)
                    await self.queue.put(file_path)
                    logger.info(f"Detected new file (poll): {file_path.name}")
            await asyncio.sleep(self.poll_interval)

    def _scan_dir(self) -> list[Path]:
        """List all supported files in the watch directory."""
        files = []
        if self.watch_dir.exists():
            for f in self.watch_dir.iterdir():
                if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                    files.append(f)
        return sorted(files)

    def stop(self) -> None:
        self._running = False
