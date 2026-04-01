"""Ingestion pipeline — connects parsing, chunking, and versioned storage."""

import json
import logging
from pathlib import Path
from dataclasses import asdict

from ..parsers.router import ParserRouter
from ..parsers.base import ParsedDocument
from .chunker import Chunker, Chunk
from .resilience import ResilientParser, FileValidator, DeadLetterQueue
from ..versioning.version_store import VersionStore

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """End-to-end pipeline: file -> validate -> parse -> chunk -> version & store.

    Supports two modes:
    - Standard: parse directly (fast, assumes clean data)
    - Resilient: validate + retry + quarantine (enterprise-grade)

    Usage:
        pipeline = IngestionPipeline(config)
        results = pipeline.process_files([Path("doc.pdf"), Path("page.html")])
    """

    def __init__(self, config: dict):
        parser_cfg = config.get("parsers", {})
        chunk_cfg = config.get("chunking", {})
        version_cfg = config.get("versioning", {})
        resilience_cfg = config.get("resilience", {})

        self.output_dir = Path(config.get("output_dir", "data/processed"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.router = ParserRouter(parser_cfg)
        self.chunker = Chunker(
            strategy=chunk_cfg.get("strategy", "fixed_size"),
            chunk_size=chunk_cfg.get("chunk_size", 512),
            chunk_overlap=chunk_cfg.get("chunk_overlap", 50),
        )
        self.version_store = VersionStore(
            versions_dir=config.get("versions_dir", "data/versions"),
            max_versions=version_cfg.get("keep_versions", 10),
        ) if version_cfg.get("enabled", True) else None

        # Resilience mode: wraps parser with validation, retry, quarantine
        self.resilient_mode = resilience_cfg.get("enabled", False)
        if self.resilient_mode:
            self.resilient_parser = ResilientParser(self.router, {
                "max_file_size_mb": resilience_cfg.get("max_file_size_mb", 100.0),
                "quarantine_dir": config.get("quarantine_dir", "data/quarantine"),
                "max_retries": resilience_cfg.get("max_retries", 2),
            })

        self._processed: list[dict] = []
        self._errors: list[dict] = []

    def process_file(self, file_path: Path) -> dict:
        """Process a single file through the pipeline.

        Returns dict with parsed doc info and chunks.
        """
        file_path = Path(file_path)
        logger.info(f"Processing: {file_path.name}")

        if self.resilient_mode:
            return self._process_file_resilient(file_path)
        return self._process_file_standard(file_path)

    def _process_file_standard(self, file_path: Path) -> dict:
        """Standard mode — direct parsing without resilience wrappers."""
        # 1. Parse
        doc: ParsedDocument = self.router.parse(file_path)
        logger.info(f"  Parsed: {doc.char_count} chars, OCR={doc.ocr_applied}")

        # 2. Chunk
        chunks: list[Chunk] = self.chunker.chunk(doc.text)
        logger.info(f"  Chunked: {len(chunks)} chunks")

        # 3. Build result
        result = {
            "source": doc.source_path,
            "file_type": doc.file_type,
            "metadata": doc.metadata,
            "ocr_applied": doc.ocr_applied,
            "parsed_at": doc.parsed_at,
            "total_chars": doc.char_count,
            "num_chunks": len(chunks),
            "chunks": [asdict(c) for c in chunks],
        }

        # 4. Save processed output
        output_file = self.output_dir / f"{file_path.stem}.json"
        output_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        logger.info(f"  Saved: {output_file}")

        self._processed.append(result)
        return result

    def _process_file_resilient(self, file_path: Path) -> dict:
        """Resilient mode — validate, parse with retry, quarantine on failure."""
        parse_result = self.resilient_parser.safe_parse(file_path)

        # If parsing failed, record error and return
        if "error" in parse_result:
            self._errors.append(parse_result)
            logger.warning(
                f"  FAILED: {file_path.name} — {parse_result['error']}"
            )
            if parse_result.get("suggestion"):
                logger.info(f"  Suggestion: {parse_result['suggestion']}")
            return parse_result

        # Chunk the extracted text
        text = parse_result.get("text", "")
        chunks = self.chunker.chunk(text)

        result = {
            "source": parse_result["source"],
            "file_type": parse_result["file_type"],
            "metadata": parse_result.get("metadata", {}),
            "ocr_applied": parse_result.get("ocr_applied", False),
            "total_chars": parse_result.get("text_length", 0),
            "num_chunks": len(chunks),
            "chunks": [asdict(c) for c in chunks],
            "validation_issues": parse_result.get("validation_issues", []),
        }

        # Save output
        output_file = self.output_dir / f"{file_path.stem}.json"
        output_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))

        self._processed.append(result)
        return result

    def process_files(self, file_paths: list[Path]) -> list[dict]:
        """Process multiple files. Returns list of results."""
        results = []
        for fp in file_paths:
            try:
                result = self.process_file(fp)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {fp}: {e}")
                results.append({"source": str(fp), "error": str(e)})

        # Version the snapshot
        if self.version_store and results:
            version_id = self.version_store.create_snapshot(
                data=results,
                description=f"Ingested {len(results)} documents",
            )
            logger.info(f"  Version snapshot: {version_id}")

        return results

    @property
    def stats(self) -> dict:
        return {
            "total_processed": len(self._processed),
            "total_errors": len(self._errors),
            "total_chunks": sum(r.get("num_chunks", 0) for r in self._processed),
            "total_chars": sum(r.get("total_chars", 0) for r in self._processed),
        }
