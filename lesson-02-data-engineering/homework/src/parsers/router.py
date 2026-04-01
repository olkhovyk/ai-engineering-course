"""Parser router — uses unstructured for all document types.

Replaces 4 hand-rolled parsers (PDF, DOCX, HTML, XLSX) with a single
library call. unstructured handles:
- Auto file type detection
- PDF text extraction (pdfminer) + OCR fallback (tesseract)
- DOCX paragraphs + tables
- HTML with script/style stripping
- XLSX across all sheets
"""

import logging
from pathlib import Path

from unstructured.partition.auto import partition

from .base import ParsedDocument

logger = logging.getLogger(__name__)


class ParserRouter:
    """Parses any supported document using unstructured.

    Usage:
        router = ParserRouter()
        doc = router.parse(Path("report.pdf"))
    """

    def __init__(self, config: dict | None = None):
        config = config or {}
        pdf_cfg = config.get("pdf", {})
        self._strategy = pdf_cfg.get("strategy", "auto")
        self._ocr_language = pdf_cfg.get("ocr_language", "eng")

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a document using unstructured's auto-partitioner."""
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        logger.info(f"Parsing {file_path.name} with unstructured")

        kwargs = {"filename": str(file_path)}

        # PDF-specific: control OCR strategy
        if suffix == ".pdf":
            kwargs["strategy"] = self._strategy
            kwargs["languages"] = [self._ocr_language]

        elements = partition(**kwargs)

        # Join all elements into plain text
        text = "\n\n".join(str(el) for el in elements if str(el).strip())

        # Check if OCR was used (from element metadata)
        ocr_applied = any(
            "ocr" in str(getattr(el.metadata, "detection_origin", "")).lower()
            for el in elements
        )

        # Collect element type stats
        element_types = {}
        for el in elements:
            type_name = type(el).__name__
            element_types[type_name] = element_types.get(type_name, 0) + 1

        metadata = {
            "element_count": len(elements),
            "element_types": element_types,
        }

        file_type = suffix.lstrip(".")
        if file_type == "htm":
            file_type = "html"

        return ParsedDocument(
            source_path=str(file_path),
            file_type=file_type,
            text=text,
            metadata=metadata,
            ocr_applied=ocr_applied,
        )

    @property
    def supported_extensions(self) -> list[str]:
        return [".pdf", ".docx", ".html", ".htm", ".xlsx", ".xls"]
