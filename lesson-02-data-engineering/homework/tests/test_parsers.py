"""Tests for document parsers (unstructured-based)."""

import pytest
from pathlib import Path

from src.parsers.base import ParsedDocument
from src.parsers.router import ParserRouter


# --- ParsedDocument ---

def test_parsed_document_char_count():
    doc = ParsedDocument(source_path="test.txt", file_type="txt", text="Hello World")
    assert doc.char_count == 11


def test_parsed_document_empty():
    doc = ParsedDocument(source_path="empty.txt", file_type="txt", text="")
    assert doc.char_count == 0
    assert doc.ocr_applied is False


# --- ParserRouter with HTML ---

@pytest.fixture
def sample_html_file(tmp_path):
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <meta name="description" content="A test page for parsing">
    <style>body { color: red; }</style>
    <script>alert("hidden");</script>
</head>
<body>
    <h1>Main Title</h1>
    <p>First paragraph with important content.</p>
    <p>Second paragraph about AI and data engineering.</p>
    <a href="https://example.com">Link 1</a>
    <a href="https://example.com/other">Link 2</a>
</body>
</html>"""
    path = tmp_path / "test.html"
    path.write_text(html)
    return path


def test_html_extracts_text(sample_html_file):
    router = ParserRouter()
    doc = router.parse(sample_html_file)

    assert doc.file_type == "html"
    assert "Main Title" in doc.text
    assert "First paragraph" in doc.text
    assert "Second paragraph" in doc.text


def test_html_strips_scripts(sample_html_file):
    router = ParserRouter()
    doc = router.parse(sample_html_file)
    assert "alert" not in doc.text


def test_html_strips_styles(sample_html_file):
    router = ParserRouter()
    doc = router.parse(sample_html_file)
    assert "color: red" not in doc.text


def test_html_has_metadata(sample_html_file):
    router = ParserRouter()
    doc = router.parse(sample_html_file)
    assert doc.metadata["element_count"] > 0
    assert isinstance(doc.metadata["element_types"], dict)


# --- Router basics ---

def test_router_handles_html(sample_html_file):
    router = ParserRouter()
    doc = router.parse(sample_html_file)
    assert doc.file_type == "html"
    assert doc.char_count > 0


def test_router_supported_extensions():
    router = ParserRouter()
    exts = router.supported_extensions
    assert ".pdf" in exts
    assert ".docx" in exts
    assert ".html" in exts
    assert ".xlsx" in exts
