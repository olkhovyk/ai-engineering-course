"""
Resume scoring with LLM.

Demonstrates how preprocessing affects AI scoring quality:
- Raw resume → lower score (noise, PII, broken formatting)
- Preprocessed resume → higher score (clean, structured)
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

JOB_DESCRIPTION = """
Senior Python Engineer

Requirements:
- 5+ years Python experience
- Experience with distributed systems and microservices
- AWS or GCP cloud experience
- CI/CD and DevOps practices
- Machine learning infrastructure experience is a plus
- Strong communication skills
- B.S. in Computer Science or equivalent

Responsibilities:
- Design and build scalable backend services
- Lead technical projects and mentor junior engineers
- Collaborate with ML team on inference infrastructure
- Maintain 99.9% uptime for production systems
"""


def score_resume(resume_text: str, job_description: str, api_key: str) -> dict:
    """Score a resume against a job description using GPT-4o-mini.

    Returns dict with score (0-100), strengths, weaknesses, and reasoning.
    """
    client = OpenAI(api_key=api_key)

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": (
                "You are an expert technical recruiter. Score the resume against "
                "the job description. Return a JSON object with:\n"
                '- "score": integer 0-100\n'
                '- "strengths": list of 2-3 key strengths\n'
                '- "weaknesses": list of 2-3 gaps or concerns\n'
                '- "recommendation": "strong_yes" | "yes" | "maybe" | "no"\n'
                '- "reasoning": 1-2 sentence explanation\n'
                "Be objective. Score based on relevant experience, skills match, "
                "and overall fit. Penalize resumes that are hard to read, contain "
                "irrelevant personal information, or lack structure."
            )},
            {"role": "user", "content": (
                f"JOB DESCRIPTION:\n{job_description}\n\n"
                f"RESUME:\n{resume_text}"
            )},
        ],
        temperature=0.1,
        max_tokens=500,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(resp.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        return {"score": 0, "error": "Failed to parse LLM response"}


def main():
    api_key = os.environ.get("OPENAI_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: Set OPENAI_KEY in .env file")
        sys.exit(1)

    # Import extract pipeline
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
    from extract import process_all_resumes

    resumes_dir = os.path.join(os.path.dirname(__file__), "data", "resumes")

    print("=" * 70)
    print("RESUME SCORING: Raw vs Preprocessed")
    print(f"Job: Senior Python Engineer")
    print("=" * 70)

    # Score RAW resumes
    print("\n--- RAW (no preprocessing) ---")
    raw_results = process_all_resumes(resumes_dir, redact=False)
    raw_scores = []
    for r in raw_results:
        score_result = score_resume(r["text"], JOB_DESCRIPTION, api_key)
        raw_scores.append(score_result)
        print(f"  {r['file']:<35} Score: {score_result.get('score', '?'):>3}/100  "
              f"Rec: {score_result.get('recommendation', '?'):<12} "
              f"PII: {r['pii_total']}")

    # Score PREPROCESSED resumes
    print("\n--- PREPROCESSED (PII redacted, normalized) ---")
    clean_results = process_all_resumes(resumes_dir, redact=True)
    clean_scores = []
    for r in clean_results:
        score_result = score_resume(r["text"], JOB_DESCRIPTION, api_key)
        clean_scores.append(score_result)
        print(f"  {r['file']:<35} Score: {score_result.get('score', '?'):>3}/100  "
              f"Rec: {score_result.get('recommendation', '?'):<12} "
              f"PII: 0")

    # Comparison
    print("\n" + "=" * 70)
    print("COMPARISON: Raw vs Preprocessed")
    print("=" * 70)
    print(f"{'Resume':<35} {'Raw':>5} {'Clean':>5} {'Delta':>6}")
    print("-" * 55)
    for i, r in enumerate(raw_results):
        rs = raw_scores[i].get("score", 0)
        cs = clean_scores[i].get("score", 0)
        delta = cs - rs
        marker = " <<<" if abs(delta) >= 5 else ""
        print(f"  {r['file']:<33} {rs:>5} {cs:>5} {delta:>+5}{marker}")

    avg_raw = sum(s.get("score", 0) for s in raw_scores) / len(raw_scores)
    avg_clean = sum(s.get("score", 0) for s in clean_scores) / len(clean_scores)
    print(f"\n  {'AVERAGE':<33} {avg_raw:>5.0f} {avg_clean:>5.0f} {avg_clean-avg_raw:>+5.0f}")
    print(f"\nPreprocessing improved average score by {avg_clean-avg_raw:+.0f} points")


if __name__ == "__main__":
    main()
