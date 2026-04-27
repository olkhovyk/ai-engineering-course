"""
Resume extraction pipeline: PDF -> clean structured JSON.

Steps:
1. Extract raw text from PDF (pdfplumber)
2. Normalize text (unicode, whitespace)
3. Detect and redact PII (SSN, DOB, address, phone, email)
4. Detect sections (Experience, Education, Skills)
5. Output structured JSON
"""

import json
import os
import re
import sys
from pathlib import Path

import pdfplumber


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from PDF using pdfplumber."""
    with pdfplumber.open(pdf_path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Clean up encoding issues, whitespace, boilerplate."""
    # Smart quotes -> straight
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    # Dashes
    text = text.replace("\u2013", "-").replace("\u2014", " - ")
    # Bullets
    text = text.replace("\u2022", "-")
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    # Remove boilerplate
    text = re.sub(r"Page \d+ of \d+", "", text)
    text = re.sub(r"\(C\) \d{4}.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"(?i)confidential.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"(?i)do not distribute.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"(?i)auto-generated.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"={5,}", "", text)
    text = re.sub(r"-{5,}", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# PII Detection & Redaction
# ---------------------------------------------------------------------------


PII_PATTERNS = {
    "email": (r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL]"),
    "phone": (r"\(\d{3}\)\s?\d{3}[\s-]?\d{4}", "[PHONE]"),
    "ssn": (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
    "dob": (r"\b\d{2}/\d{2}/\d{4}\b", "[DOB]"),
    "address": (r"\d+\s+\w+\s+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Blvd|Way)[\w\s,#.]+\d{5}", "[ADDRESS]"),
    "salary": (r"\$[\d,]+(?:/year|/yr)?", "[SALARY]"),
    "dl": (r"\b[A-Z]{2}-[A-Z]\d{3}-\d{4}-\d{4}\b", "[DL]"),
}


def detect_pii(text: str) -> dict:
    """Detect PII in text, return counts by type."""
    results = {}
    for pii_type, (pattern, _) in PII_PATTERNS.items():
        found = re.findall(pattern, text)
        if found:
            results[pii_type] = {"count": len(found), "values": found}
    return results


def redact_pii(text: str) -> str:
    """Replace PII with placeholders."""
    for pii_type, (pattern, replacement) in PII_PATTERNS.items():
        text = re.sub(pattern, replacement, text)
    return text


# ---------------------------------------------------------------------------
# Section Detection
# ---------------------------------------------------------------------------

SECTION_PATTERNS = [
    (r"(?i)\b(?:professional\s+)?summary\b", "summary"),
    (r"(?i)\b(?:work\s+)?experience\b", "experience"),
    (r"(?i)\bwork\s+history\b", "experience"),
    (r"(?i)\beducation\b", "education"),
    (r"(?i)\bskills?\b", "skills"),
    (r"(?i)\bcertifications?\b", "certifications"),
    (r"(?i)\bpublications?\b", "publications"),
    (r"(?i)\breferences?\b", "references"),
    (r"(?i)\bpersonal\s+information\b", "personal_info"),
    (r"(?i)\bsalary\b", "salary"),
]


def detect_sections(text: str) -> list[str]:
    """Detect which resume sections are present."""
    found = []
    for pattern, name in SECTION_PATTERNS:
        if re.search(pattern, text):
            found.append(name)
    return found


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def process_resume(pdf_path: str, redact: bool = True) -> dict:
    """Full pipeline: PDF -> structured JSON."""
    raw_text = extract_text_from_pdf(pdf_path)

    # Normalize
    clean_text = normalize_text(raw_text)

    # PII
    pii_found = detect_pii(clean_text)
    processed_text = redact_pii(clean_text) if redact else clean_text

    # Sections
    sections = detect_sections(processed_text)

    return {
        "file": os.path.basename(pdf_path),
        "raw_length": len(raw_text),
        "clean_length": len(clean_text),
        "processed_length": len(processed_text),
        "compression_ratio": round(len(processed_text) / len(raw_text), 2) if raw_text else 0,
        "pii_found": {k: v["count"] for k, v in pii_found.items()},
        "pii_total": sum(v["count"] for v in pii_found.values()),
        "sections_detected": sections,
        "text": processed_text,
    }


def process_all_resumes(resumes_dir: str, redact: bool = True) -> list[dict]:
    """Process all PDFs in directory."""
    results = []
    for pdf_file in sorted(Path(resumes_dir).glob("*.pdf")):
        result = process_resume(str(pdf_file), redact=redact)
        results.append(result)
    return results


if __name__ == "__main__":
    resumes_dir = os.path.join(os.path.dirname(__file__), "..", "data", "resumes")

    print("=" * 60)
    print("RESUME EXTRACTION PIPELINE")
    print("=" * 60)

    # Process without PII redaction (raw)
    print("\n--- RAW (no PII redaction) ---")
    raw_results = process_all_resumes(resumes_dir, redact=False)
    for r in raw_results:
        print(f"  {r['file']:<35} {r['raw_length']:>5} chars  PII: {r['pii_total']}  sections: {r['sections_detected']}")

    # Process with PII redaction
    print("\n--- PREPROCESSED (with PII redaction) ---")
    clean_results = process_all_resumes(resumes_dir, redact=True)
    for r in clean_results:
        print(f"  {r['file']:<35} {r['processed_length']:>5} chars  PII: {r['pii_total']}  ratio: {r['compression_ratio']}")

    # Save to JSON
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "preprocessed_resumes.json")
    with open(output_path, "w") as f:
        json.dump(clean_results, f, indent=2)
    print(f"\nSaved to {output_path}")
