"""Integration tests for the ingestion pipeline."""

import json
import pytest
from pathlib import Path

from src.ingestion.chunker import Chunker
from src.ingestion.pipeline import IngestionPipeline


# --- Chunker (langchain-backed) ---

class TestChunker:
    def test_fixed_size_basic(self):
        chunker = Chunker(strategy="fixed_size", chunk_size=100, chunk_overlap=0)
        text = "A" * 250
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2  # langchain may split differently than hand-rolled
        total_chars = sum(c.char_count for c in chunks)
        assert total_chars >= 250  # all text covered (with possible overlap)

    def test_fixed_size_overlap(self):
        chunker = Chunker(strategy="fixed_size", chunk_size=100, chunk_overlap=20)
        text = "A" * 200
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2

    def test_sentence_strategy(self):
        chunker = Chunker(strategy="sentence", chunk_size=100, chunk_overlap=0)
        text = "First sentence. Second sentence. Third sentence about AI. Fourth one here."
        chunks = chunker.chunk(text)
        assert len(chunks) >= 1
        combined = " ".join(c.text for c in chunks)
        assert "First sentence" in combined
        assert "Fourth" in combined

    def test_paragraph_strategy(self):
        chunker = Chunker(strategy="paragraph", chunk_size=200, chunk_overlap=0)
        text = "Para one content.\n\nPara two content.\n\nPara three content."
        chunks = chunker.chunk(text)
        assert len(chunks) >= 1

    def test_empty_text(self):
        chunker = Chunker()
        assert chunker.chunk("") == []
        assert chunker.chunk("   ") == []

    def test_invalid_strategy(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            Chunker(strategy="nonexistent")


# --- Pipeline integration ---

@pytest.fixture
def html_file(tmp_path):
    html = """<html><head><title>Test</title></head>
    <body><p>This is a test document for the ingestion pipeline. It contains enough
    text to be chunked into multiple pieces when using a small chunk size.</p>
    <p>Second paragraph with more content about data engineering and AI pipelines.</p>
    </body></html>"""
    path = tmp_path / "test.html"
    path.write_text(html)
    return path


@pytest.fixture
def pipeline_config(tmp_path):
    return {
        "output_dir": str(tmp_path / "processed"),
        "versions_dir": str(tmp_path / "versions"),
        "parsers": {},
        "chunking": {"strategy": "fixed_size", "chunk_size": 100, "chunk_overlap": 20},
        "versioning": {"enabled": True, "keep_versions": 5},
    }


def test_pipeline_processes_html(html_file, pipeline_config):
    pipeline = IngestionPipeline(pipeline_config)
    result = pipeline.process_file(html_file)

    assert result["file_type"] == "html"
    assert result["total_chars"] > 0
    assert result["num_chunks"] > 0
    assert len(result["chunks"]) == result["num_chunks"]


def test_pipeline_saves_output(html_file, pipeline_config, tmp_path):
    pipeline = IngestionPipeline(pipeline_config)
    pipeline.process_file(html_file)

    output_path = tmp_path / "processed" / "test.json"
    assert output_path.exists()

    data = json.loads(output_path.read_text())
    assert "chunks" in data
    assert data["file_type"] == "html"


def test_pipeline_creates_version(html_file, pipeline_config, tmp_path):
    pipeline = IngestionPipeline(pipeline_config)
    pipeline.process_files([html_file])

    versions_dir = tmp_path / "versions"
    manifest = json.loads((versions_dir / "manifest.json").read_text())
    assert len(manifest["versions"]) == 1


def test_pipeline_handles_errors(pipeline_config):
    pipeline = IngestionPipeline(pipeline_config)
    results = pipeline.process_files([Path("nonexistent.html")])
    assert len(results) == 1
    assert "error" in results[0]


def test_pipeline_stats(html_file, pipeline_config):
    pipeline = IngestionPipeline(pipeline_config)
    pipeline.process_file(html_file)

    stats = pipeline.stats
    assert stats["total_processed"] == 1
    assert stats["total_chunks"] > 0
    assert stats["total_chars"] > 0
