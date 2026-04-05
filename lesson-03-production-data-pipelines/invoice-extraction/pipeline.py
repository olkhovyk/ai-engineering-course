"""Invoice extraction pipeline — regex + LLM orchestration."""

from regex_extractor import regex_extract
from llm_extractor import llm_extract_full, llm_extract_remaining


def extract_invoice(text: str, mode: str, api_key: str) -> dict:
    """Extract invoice data.

    Args:
        text: raw invoice text
        mode: "llm_only" or "hybrid"
        api_key: OpenAI API key

    Returns:
        {
            "data": {...extracted fields...},
            "tokens_used": int,
            "time_seconds": float,
            "mode": str,
            "regex_fields_found": int (hybrid only),
            "regex_confidence": dict (hybrid only),
        }
    """
    if mode == "llm_only":
        return llm_extract_full(text, api_key)

    # Hybrid: regex first, then LLM for the rest
    regex_result = regex_extract(text)
    llm_result = llm_extract_remaining(text, regex_result, api_key)

    return {
        **llm_result,
        "regex_fields_found": regex_result["fields_found"],
        "regex_fields_total": regex_result["fields_total"],
        "regex_confidence": regex_result["confidence"],
        "regex_extracted": regex_result["extracted"],
    }
