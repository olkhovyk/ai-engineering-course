import logging
import re
from datetime import datetime, timezone

from fastapi import Header, HTTPException

from .config import get_api_keys


SUSPICIOUS_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"reveal\s+.*system\s+prompt",
    r"\bsystem\s*:",
    r"<\|im_start\|>",
    r"</s>",
    r"developer\s+message",
]

request_logger = logging.getLogger("suspicious_requests")
request_logger.setLevel(logging.INFO)
request_handler = logging.FileHandler("suspicious_requests.log", encoding="utf-8")
request_logger.addHandler(request_handler)

response_logger = logging.getLogger("suspicious_responses")
response_logger.setLevel(logging.INFO)
response_handler = logging.FileHandler("suspicious_responses.log", encoding="utf-8")
response_logger.addHandler(response_handler)


def get_api_key_metadata(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> dict:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    api_keys = get_api_keys()
    metadata = api_keys.get(x_api_key)
    if not metadata:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return {"api_key": x_api_key, **metadata}


def validate_user_input(message: str) -> None:
    if len(message) > 4_000:
        raise HTTPException(status_code=400, detail="Message is too long")

    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, message, flags=re.IGNORECASE):
            request_logger.info(
                "%s suspicious input pattern=%s message=%r",
                datetime.now(timezone.utc).isoformat(),
                pattern,
                message[:500],
            )
            raise HTTPException(status_code=400, detail="Suspicious input detected")


def output_looks_suspicious(text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in SUSPICIOUS_PATTERNS)


def log_suspicious_output(request_id: str, text: str) -> None:
    response_logger.info(
        "%s suspicious output request_id=%s text=%r",
        datetime.now(timezone.utc).isoformat(),
        request_id,
        text[:1_000],
    )

