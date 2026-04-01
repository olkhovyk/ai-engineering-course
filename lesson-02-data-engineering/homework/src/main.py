"""Main entry point — run the ingestion pipeline."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import yaml

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.pipeline import IngestionPipeline
from src.streaming.queue import DocumentQueue
from src.streaming.batcher import Batcher
from src.streaming.watcher import FileWatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def load_config() -> dict:
    config_path = PROJECT_ROOT / "configs" / "pipeline.yaml"
    if config_path.exists():
        return yaml.safe_load(config_path.read_text())
    logger.warning("No config found, using defaults")
    return {}


def resolve_paths(config: dict) -> dict:
    """Make all paths in config relative to project root."""
    for key in ("input_dir", "output_dir", "versions_dir"):
        if key in config:
            config[key] = str(PROJECT_ROOT / config[key])
    return config


def run_batch(config: dict):
    """Process all documents in input_dir (one-shot batch mode)."""
    input_dir = Path(config.get("input_dir", PROJECT_ROOT / "samples"))

    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        logger.info("Run 'python src/generate_samples.py' first to create sample documents.")
        sys.exit(1)

    supported = {".pdf", ".docx", ".html", ".htm", ".xlsx", ".xls"}
    files = [f for f in sorted(input_dir.iterdir()) if f.suffix.lower() in supported]

    if not files:
        logger.warning(f"No supported documents found in {input_dir}")
        sys.exit(0)

    logger.info(f"Found {len(files)} documents in {input_dir}")

    pipeline = IngestionPipeline(config)
    results = pipeline.process_files(files)

    # Print summary
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    stats = pipeline.stats
    print(f"  Documents processed: {stats['total_processed']}")
    print(f"  Errors:              {stats.get('total_errors', 0)}")
    print(f"  Total chunks:        {stats['total_chunks']}")
    print(f"  Total characters:    {stats['total_chars']}")

    for r in results:
        if "error" in r:
            name = Path(r["source"]).name if "source" in r else "?"
            suggestion = r.get("suggestion", "")
            quarantined = " [QUARANTINED]" if r.get("quarantined") else ""
            print(f"  FAIL: {name}{quarantined} — {r['error']}")
            if suggestion:
                print(f"        Suggestion: {suggestion}")
        else:
            name = Path(r["source"]).name if "source" in r else "?"
            chunks = r.get("num_chunks", 0)
            ocr = " [OCR]" if r.get("ocr_applied") else ""
            warnings = ""
            if r.get("validation_issues"):
                warnings = f" [WARN: {'; '.join(r['validation_issues'])}]"
            print(f"  OK:   {name} -> {chunks} chunks{ocr}{warnings}")

    print(f"\nProcessed files saved to: {config.get('output_dir', 'data/processed')}")
    print(f"Version snapshots in:     {config.get('versions_dir', 'data/versions')}")
    if config.get("resilience", {}).get("enabled"):
        print(f"Quarantine dir:           {config.get('quarantine_dir', 'data/quarantine')}")


async def run_streaming(config: dict):
    """Watch mode — monitors input dir for new files and processes in batches."""
    input_dir = Path(config.get("input_dir", PROJECT_ROOT / "samples"))
    input_dir.mkdir(parents=True, exist_ok=True)

    streaming_cfg = config.get("streaming", {})
    queue = DocumentQueue(max_size=streaming_cfg.get("max_queue_size", 100))

    pipeline = IngestionPipeline(config)

    async def process_batch(items):
        """Callback for the batcher — processes a batch of queued documents."""
        file_paths = [item.file_path for item in items]
        logger.info(f"Processing batch of {len(file_paths)} documents...")
        pipeline.process_files(file_paths)
        logger.info(f"Batch complete. Pipeline stats: {pipeline.stats}")

    batcher = Batcher(
        queue,
        batch_size=streaming_cfg.get("batch_size", 5),
        timeout_sec=streaming_cfg.get("batch_timeout_sec", 10),
    )
    batcher.on_batch(process_batch)

    watcher = FileWatcher(input_dir, queue)

    print(f"\nWatching {input_dir} for new documents...")
    print("Drop PDF, DOCX, or HTML files into this directory to process them.")
    print("Press Ctrl+C to stop.\n")

    try:
        await asyncio.gather(
            watcher.start(),
            batcher.run(),
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        watcher.stop()
        batcher.stop()


def main():
    parser = argparse.ArgumentParser(description="Document Ingestion Pipeline")
    parser.add_argument("--watch", action="store_true", help="Enable streaming watch mode")
    parser.add_argument("--input", type=str, help="Override input directory")
    parser.add_argument("--resilient", action="store_true",
                        help="Enable resilient mode (validation, retry, quarantine)")
    args = parser.parse_args()

    config = load_config()
    config = resolve_paths(config)

    if args.input:
        config["input_dir"] = args.input

    if args.resilient:
        config.setdefault("resilience", {})["enabled"] = True
        config.setdefault("quarantine_dir",
                          str(PROJECT_ROOT / "data" / "quarantine"))

    if args.watch:
        config.setdefault("streaming", {})["watch_mode"] = True
        asyncio.run(run_streaming(config))
    else:
        run_batch(config)


if __name__ == "__main__":
    main()
