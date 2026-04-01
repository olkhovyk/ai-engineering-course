"""Tests for enterprise resilience patterns (production libraries)."""

import pytest
from pathlib import Path

from src.ingestion.resilience import (
    FileValidator,
    EncodingNormalizer,
    DeadLetterQueue,
    ResilientParser,
    IngestionError,
    ErrorSeverity,
    retry_with_backoff,
)
from src.parsers.router import ParserRouter


# --- FileValidator (filetype-backed) ---

class TestFileValidator:
    def test_valid_html(self, tmp_path):
        f = tmp_path / "ok.html"
        f.write_text("<html><body>Hello</body></html>")

        v = FileValidator()
        result = v.validate(f)
        assert result.is_valid

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.pdf"
        f.write_bytes(b"")

        v = FileValidator()
        result = v.validate(f)
        assert not result.is_valid
        assert "empty" in result.issues[0].lower()

    def test_nonexistent_file(self):
        v = FileValidator()
        result = v.validate(Path("/nonexistent/file.pdf"))
        assert not result.is_valid

    def test_size_limit(self, tmp_path):
        f = tmp_path / "big.html"
        f.write_bytes(b"x" * (2 * 1024 * 1024))

        v = FileValidator(max_size_mb=1.0)
        result = v.validate(f)
        assert "too large" in result.issues[0].lower()

    def test_type_mismatch_html_as_pdf(self, tmp_path):
        f = tmp_path / "sneaky.pdf"
        f.write_text("<html><body>I'm HTML!</body></html>")

        v = FileValidator()
        result = v.validate(f)
        assert result.type_mismatch
        assert result.detected_type == "html"

    def test_xlsx_not_flagged_as_zip(self, tmp_path):
        """XLSX is ZIP-based — should not produce a mismatch warning."""
        # Create a minimal valid xlsx
        try:
            from openpyxl import Workbook
            f = tmp_path / "test.xlsx"
            wb = Workbook()
            wb.active.append(["test"])
            wb.save(str(f))

            v = FileValidator()
            result = v.validate(f)
            mismatch_issues = [i for i in result.issues if "mismatch" in i.lower()]
            assert len(mismatch_issues) == 0
        except ImportError:
            pytest.skip("openpyxl not installed")


# --- EncodingNormalizer (charset-normalizer-backed) ---

class TestEncodingNormalizer:
    def test_utf8(self, tmp_path):
        f = tmp_path / "utf8.html"
        f.write_text("Hello World", encoding="utf-8")

        text, enc = EncodingNormalizer.read_with_best_encoding(f)
        assert "Hello World" in text

    def test_utf8_bom(self, tmp_path):
        f = tmp_path / "bom.html"
        f.write_bytes(b"\xef\xbb\xbf<html><body>BOM test</body></html>")

        text, enc = EncodingNormalizer.read_with_best_encoding(f)
        assert "BOM test" in text

    def test_cp1251(self, tmp_path):
        f = tmp_path / "cyrillic.html"
        cyrillic = "Привіт світ"
        f.write_bytes(cyrillic.encode("cp1251"))

        text, enc = EncodingNormalizer.read_with_best_encoding(f)
        assert len(text) > 0

    def test_latin1(self, tmp_path):
        f = tmp_path / "latin.html"
        f.write_bytes("Geräteübersicht".encode("latin-1"))

        text, enc = EncodingNormalizer.read_with_best_encoding(f)
        assert len(text) > 0


# --- retry_with_backoff (tenacity-backed) ---

class TestRetryWithBackoff:
    def test_succeeds_first_try(self):
        result = retry_with_backoff(lambda: 42, max_retries=3, base_delay=0.01)
        assert result == 42

    def test_succeeds_after_retry(self):
        attempts = {"count": 0}

        def flaky():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise IOError("transient")
            return "ok"

        result = retry_with_backoff(
            flaky, max_retries=3, base_delay=0.01, backoff_factor=1.0
        )
        assert result == "ok"
        assert attempts["count"] == 3

    def test_exhausts_retries(self):
        def always_fail():
            raise IOError("permanent")

        with pytest.raises(IOError):
            retry_with_backoff(
                always_fail, max_retries=2, base_delay=0.01, backoff_factor=1.0
            )

    def test_no_retry_on_non_retryable(self):
        attempts = {"count": 0}

        def bad_value():
            attempts["count"] += 1
            raise ValueError("bad")

        with pytest.raises(ValueError):
            retry_with_backoff(bad_value, max_retries=3, base_delay=0.01)

        assert attempts["count"] == 1


# --- DeadLetterQueue ---

class TestDeadLetterQueue:
    def test_quarantine_creates_files(self, tmp_path):
        dlq = DeadLetterQueue(quarantine_dir=tmp_path / "quarantine")

        src = tmp_path / "bad.pdf"
        src.write_bytes(b"bad data")

        error = IngestionError(
            file_path=str(src),
            error_type="ParseError",
            message="corrupted PDF",
            severity=ErrorSeverity.FATAL,
            suggestion="Get a new copy",
        )
        dest = dlq.quarantine(src, error)

        assert dest.exists()
        assert (tmp_path / "quarantine" / "bad_error.json").exists()
        assert dlq.error_count == 1

    def test_error_tracking(self, tmp_path):
        dlq = DeadLetterQueue(quarantine_dir=tmp_path / "q")

        for i in range(3):
            src = tmp_path / f"file{i}.pdf"
            src.write_bytes(b"x")
            dlq.quarantine(src, IngestionError(
                file_path=str(src), error_type="err",
                message=f"error {i}", severity=ErrorSeverity.FATAL,
                suggestion="fix it",
            ))

        assert dlq.error_count == 3
        assert len(dlq.errors) == 3


# --- ResilientParser (integration) ---

class TestResilientParser:
    def test_rejects_empty_file(self, tmp_path):
        f = tmp_path / "empty.html"
        f.write_bytes(b"")

        router = ParserRouter()
        rp = ResilientParser(router, {"quarantine_dir": str(tmp_path / "q")})
        result = rp.safe_parse(f)

        assert "error" in result
        assert result["quarantined"] is True

    def test_parses_valid_html(self, tmp_path):
        f = tmp_path / "good.html"
        f.write_text("<html><body><p>Good document</p></body></html>")

        router = ParserRouter()
        rp = ResilientParser(router, {"quarantine_dir": str(tmp_path / "q")})
        result = rp.safe_parse(f)

        assert "error" not in result
        assert result["text_length"] > 0
        assert result["file_type"] == "html"
