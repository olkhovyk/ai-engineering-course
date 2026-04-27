"""Load invoice text from PDF files."""

import os
from pathlib import Path

import pdfplumber


def extract_text(pdf_path: str) -> str:
    """Extract raw text from a PDF file."""
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def list_invoices(invoices_dir: str | None = None) -> list[dict]:
    """List all PDF invoices in folder with extracted text."""
    if invoices_dir is None:
        invoices_dir = os.path.join(os.path.dirname(__file__), "invoices")
    path = Path(invoices_dir)
    if not path.exists():
        return []
    result = []
    for f in sorted(path.glob("*.pdf")):
        text = extract_text(str(f))
        if text.strip():
            result.append({"file": f.name, "path": str(f), "text": text.strip()})
    return result
