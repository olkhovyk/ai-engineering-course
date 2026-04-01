"""Resilience patterns for enterprise document ingestion.

Uses production libraries:
- filetype: file type detection via magic bytes
- charset-normalizer: encoding detection
- tenacity: retry with backoff

Patterns:
1. File validation (magic bytes, size limits, empty checks)
2. Encoding detection and normalization
3. Retry with exponential backoff
4. Error classification (retryable vs fatal)
5. Dead letter queue (quarantine for unfixable files)
"""

import json
import logging
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import filetype as filetype_lib
from charset_normalizer import from_bytes
from tenacity import (
    Retrying,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    RECOVERABLE = "recoverable"
    DEGRADED = "degraded"
    FATAL = "fatal"


@dataclass
class ValidationResult:
    is_valid: bool
    file_path: Path
    declared_type: str
    detected_type: str | None
    file_size: int
    issues: list[str] = field(default_factory=list)

    @property
    def type_mismatch(self) -> bool:
        return (
            self.detected_type is not None
            and self.declared_type != self.detected_type
        )


@dataclass
class IngestionError:
    file_path: str
    error_type: str
    message: str
    severity: ErrorSeverity
    suggestion: str


# ---------------------------------------------------------------------------
# File Validator — uses filetype library for magic byte detection
# ---------------------------------------------------------------------------
class FileValidator:
    """Pre-flight checks: empty? too large? wrong type?

    Uses the `filetype` library for binary file type detection,
    with a text-based fallback for HTML (which has no magic bytes).
    """

    # Map filetype MIME types to simple names
    MIME_MAP = {
        "application/pdf": "pdf",
        "application/zip": "zip",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    }

    # ZIP-based formats that should not trigger mismatch warnings
    ZIP_BASED = {"docx", "xlsx", "pptx", "odt", "ods"}

    def __init__(self, max_size_mb: float = 100.0):
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)

    def validate(self, file_path: Path) -> ValidationResult:
        file_path = Path(file_path)
        issues = []

        if not file_path.exists():
            return ValidationResult(
                is_valid=False, file_path=file_path,
                declared_type="", detected_type=None, file_size=0,
                issues=["File does not exist"],
            )

        file_size = file_path.stat().st_size
        declared_type = file_path.suffix.lstrip(".").lower()

        if file_size == 0:
            return ValidationResult(
                is_valid=False, file_path=file_path,
                declared_type=declared_type, detected_type=None,
                file_size=0, issues=["File is empty (0 bytes)"],
            )

        if file_size > self.max_size_bytes:
            issues.append(
                f"File too large: {file_size / 1024 / 1024:.1f} MB "
                f"(limit: {self.max_size_bytes / 1024 / 1024:.0f} MB)"
            )

        detected_type = self._detect_type(file_path)
        if detected_type and detected_type != declared_type:
            compatible = (
                {declared_type, detected_type} <= {"html", "htm"}
                or (detected_type == "zip" and declared_type in self.ZIP_BASED)
            )
            if not compatible:
                issues.append(
                    f"Type mismatch: extension is .{declared_type} "
                    f"but content looks like {detected_type}"
                )

        return ValidationResult(
            is_valid=len(issues) == 0 or all("mismatch" in i for i in issues),
            file_path=file_path,
            declared_type=declared_type,
            detected_type=detected_type,
            file_size=file_size,
            issues=issues,
        )

    def _detect_type(self, file_path: Path) -> str | None:
        """Detect file type using filetype library + HTML fallback."""
        kind = filetype_lib.guess(str(file_path))
        if kind is not None:
            return self.MIME_MAP.get(kind.mime, kind.extension)

        # filetype can't detect text-based formats (HTML) — check manually
        try:
            header = file_path.read_bytes()[:512].lower()
            if b"<html" in header or b"<!doctype" in header:
                return "html"
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Encoding Normalizer — uses charset-normalizer
# ---------------------------------------------------------------------------
class EncodingNormalizer:
    """Detect and normalize text encoding using charset-normalizer.

    Replaces hand-rolled encoding detection loop. charset-normalizer
    is the successor to chardet — faster and more accurate.
    """

    @classmethod
    def read_with_best_encoding(cls, file_path: Path) -> tuple[str, str]:
        raw = file_path.read_bytes()
        result = from_bytes(raw).best()
        if result is None:
            return raw.decode("utf-8", errors="replace"), "utf-8 (forced)"
        return str(result), result.encoding


# ---------------------------------------------------------------------------
# Retry with Backoff — uses tenacity
# ---------------------------------------------------------------------------
def retry_with_backoff(
    fn,
    max_retries: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (IOError, OSError, TimeoutError),
):
    """Retry a function with exponential backoff using tenacity.

    Same interface as before, but backed by tenacity internally.
    """
    retryer = Retrying(
        stop=stop_after_attempt(max_retries + 1),
        wait=wait_exponential(multiplier=base_delay, exp_base=backoff_factor),
        retry=retry_if_exception_type(retryable_exceptions),
        reraise=True,
    )
    return retryer(fn)


# ---------------------------------------------------------------------------
# Dead Letter Queue
# ---------------------------------------------------------------------------
class DeadLetterQueue:
    """Quarantine for documents that can't be processed."""

    def __init__(self, quarantine_dir: str | Path = "data/quarantine"):
        self.quarantine_dir = Path(quarantine_dir)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self._errors: list[IngestionError] = []

    def quarantine(self, file_path: Path, error: IngestionError) -> Path:
        file_path = Path(file_path)
        self._errors.append(error)

        dest = self.quarantine_dir / file_path.name
        if file_path.exists():
            shutil.copy2(file_path, dest)

        report_path = self.quarantine_dir / f"{file_path.stem}_error.json"
        report_path.write_text(json.dumps({
            "file": str(file_path),
            "error_type": error.error_type,
            "message": error.message,
            "severity": error.severity.value,
            "suggestion": error.suggestion,
        }, indent=2))

        logger.warning(f"Quarantined {file_path.name}: {error.message}")
        return dest

    @property
    def error_count(self) -> int:
        return len(self._errors)

    @property
    def errors(self) -> list[IngestionError]:
        return list(self._errors)


# ---------------------------------------------------------------------------
# Resilient Parser Wrapper
# ---------------------------------------------------------------------------
class ResilientParser:
    """Wraps the parser router with all resilience patterns.

    Flow: validate → parse with retry → quarantine on failure.
    """

    def __init__(self, parser_router, config: dict | None = None):
        config = config or {}
        self.router = parser_router
        self.validator = FileValidator(
            max_size_mb=config.get("max_file_size_mb", 100.0)
        )
        self.dlq = DeadLetterQueue(
            quarantine_dir=config.get("quarantine_dir", "data/quarantine")
        )
        self.max_retries = config.get("max_retries", 2)

    def safe_parse(self, file_path: Path) -> dict:
        file_path = Path(file_path)

        # Step 1: Validate
        validation = self.validator.validate(file_path)
        if not validation.is_valid:
            error = IngestionError(
                file_path=str(file_path),
                error_type="validation_failed",
                message="; ".join(validation.issues),
                severity=ErrorSeverity.FATAL,
                suggestion=self._suggest_fix(validation),
            )
            self.dlq.quarantine(file_path, error)
            return {"source": str(file_path), "error": error.message,
                    "suggestion": error.suggestion, "quarantined": True}

        if validation.type_mismatch:
            logger.warning(
                f"Type mismatch for {file_path.name}: "
                f"extension=.{validation.declared_type}, "
                f"detected={validation.detected_type}"
            )

        # Step 2: Parse with retry
        try:
            doc = retry_with_backoff(
                fn=lambda: self.router.parse(file_path),
                max_retries=self.max_retries,
                retryable_exceptions=(IOError, OSError, TimeoutError),
            )
            return {
                "source": str(file_path),
                "file_type": doc.file_type,
                "text_length": doc.char_count,
                "ocr_applied": doc.ocr_applied,
                "metadata": doc.metadata,
                "validation_issues": validation.issues,
                "text": doc.text,
            }
        except Exception as e:
            severity = self._classify_error(e)
            error = IngestionError(
                file_path=str(file_path),
                error_type=type(e).__name__,
                message=str(e),
                severity=severity,
                suggestion=self._suggest_fix_for_error(e, file_path),
            )
            self.dlq.quarantine(file_path, error)
            return {"source": str(file_path), "error": str(e),
                    "suggestion": error.suggestion, "quarantined": True}

    def _classify_error(self, error: Exception) -> ErrorSeverity:
        error_str = str(error).lower()
        if any(kw in error_str for kw in ["encrypt", "password", "permission"]):
            return ErrorSeverity.FATAL
        if any(kw in error_str for kw in ["timeout", "busy", "locked"]):
            return ErrorSeverity.RECOVERABLE
        if any(kw in error_str for kw in ["truncat", "corrupt", "invalid"]):
            return ErrorSeverity.DEGRADED
        return ErrorSeverity.FATAL

    def _suggest_fix(self, validation: ValidationResult) -> str:
        suggestions = []
        for issue in validation.issues:
            if "empty" in issue.lower():
                suggestions.append("File is empty. Check the source system for export errors.")
            elif "too large" in issue.lower():
                suggestions.append("Split the file or increase max_file_size_mb in config.")
            elif "mismatch" in issue.lower():
                suggestions.append(
                    f"Rename to correct extension (.{validation.detected_type}) "
                    f"or fix the source system."
                )
        return " ".join(suggestions) if suggestions else "Investigate the file manually."

    def _suggest_fix_for_error(self, error: Exception, file_path: Path) -> str:
        error_str = str(error).lower()
        if "encrypt" in error_str or "password" in error_str:
            return "File is password-protected. Obtain the password or request an unprotected version."
        if "codec" in error_str or "encoding" in error_str:
            return "Encoding issue. The file may use a non-standard character encoding."
        if "corrupt" in error_str or "truncat" in error_str:
            return "File is corrupted. Request a fresh copy from the source system."
        return "Check logs and investigate the file manually."
