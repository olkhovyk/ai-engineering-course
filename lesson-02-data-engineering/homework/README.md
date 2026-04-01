# Lesson 2: Data Engineering for AI — Ingestion Pipeline

## What you'll build

A document ingestion pipeline that:

1. **Parses PDF, DOCX, HTML** documents and extracts text + metadata
2. **Applies OCR** when scanned/image-based PDFs are detected
3. **Streams documents** through a queue with configurable batching
4. **Versions** every data snapshot so you can reproduce any past state

## Architecture

```
samples/          Raw files (PDF, DOCX, HTML)
   |
   v
[FileWatcher] ── detects new files
   |
   v
[Queue] ── async queue with configurable batch size
   |
   v
[Parser Router] ── picks parser by file type
   |    |    |
  PDF  DOCX  HTML
   |    |    |
   v    v    v
[OCR?] ── falls back to OCR if text extraction yields nothing
   |
   v
[Chunker] ── splits text into chunks for AI consumption
   |
   v
[Versioned Store] ── saves processed data with version metadata
```

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

```bash
# 1. Generate sample documents to work with
python src/generate_samples.py

# 2. Run the full pipeline on sample documents
python src/main.py

# 3. Run with streaming mode (file watcher + queue)
python src/main.py --watch

# 4. Check data versions
python src/versioning/version_store.py --list

# 5. Run tests
pytest tests/ -v
```

## Project Structure

```
src/
  main.py                  — Entry point, orchestrates the pipeline
  generate_samples.py      — Creates sample PDF/DOCX/HTML files
  parsers/
    base.py                — Base parser interface
    pdf_parser.py          — PDF text extraction + OCR fallback
    docx_parser.py         — DOCX parsing
    html_parser.py         — HTML parsing with tag stripping
    router.py              — Routes files to correct parser
  streaming/
    queue.py               — Async document queue
    batcher.py             — Batching logic (size / time window)
    watcher.py             — File system watcher for new documents
  ingestion/
    chunker.py             — Text chunking strategies
    pipeline.py            — Connects all stages together
  versioning/
    version_store.py       — Data versioning with hash-based snapshots
configs/
  pipeline.yaml            — Pipeline configuration
tests/
  test_parsers.py          — Parser unit tests
  test_pipeline.py         — Integration tests
  test_versioning.py       — Versioning tests
```

## Key Concepts Practiced

| Concept | Where in code |
|---|---|
| PDF/DOCX/HTML parsing | `src/parsers/` |
| OCR fallback | `src/parsers/pdf_parser.py` |
| Streaming ingestion | `src/streaming/watcher.py` + `queue.py` |
| Queue + batching | `src/streaming/batcher.py` |
| Data versioning | `src/versioning/version_store.py` |
| Pipeline orchestration | `src/ingestion/pipeline.py` |
