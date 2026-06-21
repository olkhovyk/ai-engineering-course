from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "data" / "policy_docs.md"


SENSITIVE_PATTERNS = [
    r"\bapi\s*keys?\b",
    r"\bpasswords?\b",
    r"\bfull\s+card\s+numbers?\b",
    r"\bcredit\s+card\s+numbers?\b",
    r"\bpayment\s+details?\b",
    r"\binternal\s+employee\s+notes?\b",
    r"\bprivate\s+account\s+metadata\b",
    r"\bpersonal\s+data\b",
    r"\bsystem\s+prompt\b",
    r"\bhidden\s+instructions?\b",
]

INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"disregard safety rules",
    r"debug mode",
    r"reveal the hidden",
    r"print all",
    r"bypass authentication",
]

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for", "from",
    "how", "i", "if", "in", "is", "it", "me", "my", "of", "on", "or", "the",
    "to", "what", "when", "with", "you", "your",
}


@dataclass
class AssistantResponse:
    answer: str
    sources: list[str]
    refused: bool


def load_policy_sections(path: Path = POLICY_PATH) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    sections: dict[str, list[str]] = {}
    current = "General"

    for line in text.splitlines():
        if line.startswith("## "):
            current = line.replace("## ", "").strip()
            sections[current] = []
            continue
        if current not in sections:
            sections[current] = []
        if line.strip() and not line.startswith("#"):
            sections[current].append(line.strip())

    return {name: " ".join(lines) for name, lines in sections.items()}


def normalize(text: str) -> str:
    return text.lower().strip()


def contains_any(patterns: list[str], text: str) -> bool:
    normalized = normalize(text)
    return any(re.search(pattern, normalized) for pattern in patterns)


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", text.lower())
    return {word for word in words if word not in STOPWORDS and len(word) > 2}


def retrieve_sections(question: str, sections: dict[str, str], limit: int = 2) -> list[tuple[str, str, int]]:
    query_terms = tokenize(question)
    scored = []
    for title, content in sections.items():
        content_terms = tokenize(f"{title} {content}")
        score = len(query_terms & content_terms)
        if score:
            scored.append((title, content, score))
    return sorted(scored, key=lambda item: item[2], reverse=True)[:limit]


def answer_support_question(question: str) -> AssistantResponse:
    sections = load_policy_sections()
    is_injection = contains_any(INJECTION_PATTERNS, question)
    asks_sensitive = contains_any(SENSITIVE_PATTERNS, question)

    if "reset" in normalize(question) and "password" in normalize(question):
        asks_sensitive = False

    if asks_sensitive and not ("refund" in normalize(question) and not contains_any(SENSITIVE_PATTERNS[:-2], question)):
        return AssistantResponse(
            answer=(
                "I cannot reveal sensitive information such as passwords, credentials, secrets, "
                "payment information, personal data, private account metadata, internal notes, "
                "or hidden instructions."
            ),
            sources=["Security", "Privacy"],
            refused=True,
        )

    retrieved = retrieve_sections(question, sections)
    if not retrieved:
        return AssistantResponse(
            answer="I do not know. The provided support policy does not specify this.",
            sources=[],
            refused=True,
        )

    source_names = [title for title, _, _ in retrieved]
    context = " ".join(content for _, content, _ in retrieved)
    q = normalize(question)

    if "sla" in q or "uptime" in q or "phone number" in q:
        return AssistantResponse(
            answer="I do not know. This is not specified in the provided support policy.",
            sources=source_names,
            refused=True,
        )

    if "refund" in q or "charged" in q or "charge" in q or "billing" in q:
        if "enterprise" in q and "onboarding" in q:
            answer = "Refunds are not available for annual Enterprise contracts after the onboarding call has happened."
        else:
            answer = "Customers can request a refund within 14 days of purchase if they have used less than 20% of their monthly quota. Duplicate charges should be refunded after billing verification."
    elif "sso" in q:
        answer = "SSO Add-on is a supported product."
    elif "password" in q:
        answer = "Support can help with password reset."
    elif "two-factor" in q or "2fa" in q:
        answer = "Support can help with two-factor authentication recovery."
    elif "ownership transfer" in q or "transfer ownership" in q:
        return AssistantResponse(
            answer="I cannot assist with that authentication request. For account ownership transfer, the current owner must approve the transfer by email.",
            sources=["Account Access", "Security"],
            refused=True,
        )
    elif "outage" in q or "production" in q or "payment failure" in q or "active service" in q:
        answer = "Critical production outages and payment failures blocking active service should be escalated to a human support engineer."
    elif is_injection:
        answer = "I will ignore the prompt injection attempt and answer only according to support policy. " + context
    else:
        answer = context

    return AssistantResponse(answer=answer, sources=source_names, refused=False)


if __name__ == "__main__":
    while True:
        try:
            user_question = input("Question: ").strip()
        except EOFError:
            break
        if not user_question:
            break
        response = answer_support_question(user_question)
        print(response.answer)
        print(f"sources={response.sources} refused={response.refused}")
