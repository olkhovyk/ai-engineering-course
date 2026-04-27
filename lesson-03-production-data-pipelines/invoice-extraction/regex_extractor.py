"""Regex-based field extraction — cheap preprocessing layer.

Extracts structured fields from invoice text using patterns.
Returns extracted values with confidence levels.
"""

import re

# --- Patterns ---

PATTERNS = {
    "invoice_number": [
        (r"(?:Invoice|Inv\.?|Factura)\s*(?:#|No\.?|Number|Numero de Factura)?:?\s*(INV-[\w-]+|FACT-[\w-]+|inv[\w-]+)", "HIGH"),
        (r"#\s*([\w-]+)", "LOW"),
    ],
    "date": [
        (r"(?:Invoice\s+)?Date:?\s*(\w+ \d{1,2},? \d{4})", "HIGH"),
        (r"(?:Fecha|Date):?\s*(\d{1,2}/\d{1,2}/\d{4})", "HIGH"),
        (r"date:?\s*(\w{3}\s+\d{1,2}\s+\d{4})", "MEDIUM"),
    ],
    "due_date": [
        (r"(?:Due\s+Date|Fecha de Vencimiento|due):?\s*(\w+ \d{1,2},? \d{4})", "HIGH"),
        (r"(?:Due|due):?\s*(\d{1,2}/\d{1,2}/\d{4})", "HIGH"),
        (r"due:?\s*(\w{3}\s+\d{1,2}\s+\d{4})", "MEDIUM"),
    ],
    "total": [
        (r"(?:TOTAL|Total|total)\s*:?\s*\$?([\d,]+\.\d{2})", "HIGH"),
        (r"total\s+due:?\s*\$?([\d,]+\.\d{2})", "HIGH"),
    ],
    "subtotal": [
        (r"(?:Subtotal|Sub-total|subtotal)\s*:?\s*\$?([\d,]+\.\d{2})", "HIGH"),
    ],
    "tax": [
        (r"(?:Tax|IVA|tax)\s*(?:\(\d+%?\))?\s*:?\s*\$?([\d,]+\.\d{2})", "HIGH"),
    ],
    "email": [
        (r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", "HIGH"),
    ],
    "phone": [
        (r"\((\d{3})\)\s?(\d{3})[\s.-]?(\d{4})", "HIGH"),
        (r"\+\d{1,2}\s?\d{2}\s?\d{4}\s?\d{4}", "MEDIUM"),
    ],
    "payment_terms": [
        (r"(?:Payment\s+Terms|Terms|Condiciones de Pago|payment)\s*:?\s*(Net\s+\d+|\d+\s+d[iy]as?\s+neto?)", "HIGH"),
        (r"pay\s+within\s+(\d+\s+days)", "MEDIUM"),
    ],
    "po_reference": [
        (r"(?:PO|P\.O\.|po)\s*(?:ref|reference|#)?:?\s*(PO-[\w-]+)", "HIGH"),
    ],
}


def regex_extract(text: str) -> dict:
    """Extract fields using regex patterns.

    Returns:
        {
            "extracted": {"field": "value", ...},
            "confidence": {"field": "HIGH"|"MEDIUM"|"LOW"|"NONE", ...},
            "fields_found": int,
            "fields_total": int,
            "remaining_text": str  # text with extracted values removed
        }
    """
    extracted = {}
    confidence = {}
    remaining = text

    for field, patterns in PATTERNS.items():
        found = False
        for pattern, conf in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1) if match.lastindex else match.group(0)
                # Format phone
                if field == "phone" and match.lastindex and match.lastindex >= 3:
                    value = f"({match.group(1)}) {match.group(2)}-{match.group(3)}"
                extracted[field] = value.strip()
                confidence[field] = conf
                found = True
                break
        if not found:
            confidence[field] = "NONE"

    fields_found = sum(1 for v in confidence.values() if v != "NONE")

    return {
        "extracted": extracted,
        "confidence": confidence,
        "fields_found": fields_found,
        "fields_total": len(PATTERNS),
        "remaining_text": remaining,
    }
