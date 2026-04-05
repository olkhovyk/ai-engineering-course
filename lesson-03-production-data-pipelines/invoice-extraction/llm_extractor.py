"""LLM-based invoice extraction using OpenAI GPT-4o-mini."""

import json
import time

TARGET_SCHEMA = """{
  "invoice_number": "string",
  "date": "string",
  "due_date": "string",
  "vendor_name": "string",
  "vendor_address": "string",
  "vendor_email": "string",
  "vendor_phone": "string",
  "customer_name": "string",
  "customer_address": "string",
  "line_items": [{"description": "string", "quantity": "number", "unit_price": "number", "total": "number"}],
  "subtotal": "number",
  "tax": "number",
  "total": "number",
  "payment_terms": "string",
  "po_reference": "string",
  "notes": "string"
}"""


def llm_extract_full(text: str, api_key: str) -> dict:
    """Mode 1: Send ENTIRE text to LLM. No preprocessing. Expensive."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    start = time.time()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": (
                "You are an invoice data extractor. Extract ALL fields from the invoice text "
                "into the exact JSON schema below. If a field is not found, use null. "
                f"Schema:\n{TARGET_SCHEMA}"
            )},
            {"role": "user", "content": f"Extract fields from this invoice:\n\n{text}"},
        ],
        temperature=0,
        max_tokens=1500,
        response_format={"type": "json_object"},
    )
    elapsed = time.time() - start

    try:
        result = json.loads(resp.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        result = {}

    tokens_used = resp.usage.total_tokens if resp.usage else 0

    return {
        "data": result,
        "tokens_used": tokens_used,
        "time_seconds": round(elapsed, 2),
        "mode": "llm_only",
    }


def llm_extract_remaining(text: str, pre_extracted: dict, api_key: str) -> dict:
    """Mode 2: Regex handles simple fields, LLM only extracts what's missing.

    Key optimization: we strip already-extracted values from the text
    and ask LLM to extract ONLY the missing fields + line items.
    This cuts input tokens significantly.
    """
    from openai import OpenAI
    import re as _re
    client = OpenAI(api_key=api_key)

    already = pre_extracted.get("extracted", {})
    confidence = pre_extracted.get("confidence", {})
    missing = [f for f, c in confidence.items() if c == "NONE"]
    low_conf = [f for f, c in confidence.items() if c in ("LOW", "MEDIUM")]

    # Strip already-extracted values from text to reduce tokens
    short_text = text
    for val in already.values():
        if val and len(val) > 3:
            short_text = short_text.replace(val, "")
    # Remove empty lines created by stripping
    short_text = _re.sub(r"\n{3,}", "\n\n", short_text).strip()

    # Minimal schema — only fields LLM needs to find
    missing_schema = {
        "vendor_name": "string",
        "vendor_address": "string",
        "customer_name": "string",
        "customer_address": "string",
        "line_items": [{"description": "string", "quantity": "number", "unit_price": "number", "total": "number"}],
        "notes": "string or null",
    }
    # Add any regex-missed simple fields
    for f in missing + low_conf:
        if f not in missing_schema:
            missing_schema[f] = "string or number"

    prompt = (
        f"Extract ONLY these fields from the invoice text:\n"
        f"{json.dumps(missing_schema, indent=2)}\n\n"
        f"Invoice text:\n{short_text}"
    )

    start = time.time()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Extract only the requested fields. Return JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=1000,
        response_format={"type": "json_object"},
    )
    elapsed = time.time() - start

    try:
        llm_fields = json.loads(resp.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        llm_fields = {}

    # Merge: regex fields (trusted) + LLM fields (for gaps)
    merged = {
        "invoice_number": already.get("invoice_number"),
        "date": already.get("date"),
        "due_date": already.get("due_date"),
        "vendor_name": llm_fields.get("vendor_name"),
        "vendor_address": llm_fields.get("vendor_address"),
        "vendor_email": already.get("email"),
        "vendor_phone": already.get("phone"),
        "customer_name": llm_fields.get("customer_name"),
        "customer_address": llm_fields.get("customer_address"),
        "line_items": llm_fields.get("line_items", []),
        "subtotal": _parse_number(already.get("subtotal")),
        "tax": _parse_number(already.get("tax")),
        "total": _parse_number(already.get("total")),
        "payment_terms": already.get("payment_terms"),
        "po_reference": already.get("po_reference") or llm_fields.get("po_reference"),
        "notes": llm_fields.get("notes"),
    }
    # Fill any remaining missing from LLM
    for f in missing + low_conf:
        mapped = f if f in merged else None
        if mapped and merged.get(mapped) is None and f in llm_fields:
            merged[mapped] = llm_fields[f]

    tokens_used = resp.usage.total_tokens if resp.usage else 0

    return {
        "data": merged,
        "tokens_used": tokens_used,
        "time_seconds": round(elapsed, 2),
        "mode": "hybrid",
    }


def _parse_number(val: str | None) -> float | None:
    """Parse '$1,234.56' → 1234.56."""
    if not val:
        return None
    import re as _re
    clean = _re.sub(r"[,$]", "", val)
    try:
        return float(clean)
    except ValueError:
        return None
