"""Load documents from PDF files with metadata extraction."""

import os
import re
from pathlib import Path

import pdfplumber


# Metadata mapping: filename pattern -> metadata
_DOC_METADATA = {
    "patient_inquiry": {"department": "Patient Services", "doc_type": "inquiry"},
    "billing_inquiry": {"department": "Billing", "doc_type": "inquiry"},
    "insurance_verification": {"department": "Billing", "doc_type": "verification"},
    "lab_results": {"department": "Laboratory", "doc_type": "results"},
    "prescription_refill": {"department": "Pharmacy", "doc_type": "prescription"},
    "scheduling_policy": {"department": "Administration", "doc_type": "policy"},
    "compliance_handbook": {"department": "Compliance", "doc_type": "policy"},
    "staff_meeting": {"department": "Administration", "doc_type": "meeting_notes"},
    "urgent_care": {"department": "Clinical", "doc_type": "protocol"},
}


def _extract_metadata(pdf_file: Path, text: str) -> dict:
    """Extract metadata from PDF properties and filename."""
    name = pdf_file.stem

    # Department and doc_type from filename
    dept = "General"
    doc_type = "document"
    for pattern, meta in _DOC_METADATA.items():
        if pattern in name:
            dept = meta["department"]
            doc_type = meta["doc_type"]
            break

    # Year from filename (e.g., scheduling_policy_2024_current)
    year_match = re.search(r"(20\d{2})", name)
    year = int(year_match.group(1)) if year_match else None

    # Try PDF metadata
    author = None
    title = None
    try:
        with pdfplumber.open(pdf_file) as pdf:
            info = pdf.metadata or {}
            author = info.get("Author") or info.get("author")
            title = info.get("Title") or info.get("title")
            if not year and info.get("CreationDate"):
                cd = info["CreationDate"]
                y = re.search(r"20\d{2}", cd)
                if y:
                    year = int(y.group())
    except Exception:
        pass

    # Version from filename
    version = "current"
    if "outdated" in name:
        version = "outdated"
    elif "duplicate" in name or "copy" in name:
        version = "duplicate"

    return {
        "department": dept,
        "doc_type": doc_type,
        "year": year,
        "version": version,
        "author": author,
        "title": title or name.replace("_", " ").title(),
    }


def load_docs_from_folder(docs_dir: str | None = None) -> list[dict]:
    """Load all PDF documents from docs/ folder with metadata."""
    if docs_dir is None:
        docs_dir = os.path.join(os.path.dirname(__file__), "docs")
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        return []
    docs = []
    for pdf_file in sorted(docs_path.glob("*.pdf")):
        try:
            with pdfplumber.open(pdf_file) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            if text.strip():
                metadata = _extract_metadata(pdf_file, text)
                docs.append({
                    "id": pdf_file.stem,
                    "text": text.strip(),
                    "source": pdf_file.name,
                    "metadata": metadata,
                })
        except Exception:
            continue
    return docs
