# RAG Demo — Healthcare Clinic

Interactive Streamlit demo showing how preprocessing affects RAG quality in a healthcare setting.

Without preprocessing, the chatbot leaks patient emails, phone numbers, and SSNs in its answers (HIPAA violation). Toggle each preprocessing step and watch the answer quality improve.

## What This Project Demonstrates

- **Broken by default → fix incrementally** — all preprocessing OFF → PII leak visible → turn ON step by step → quality improves
- **PII Redaction is not optional** — without it, GPT includes real patient contact info in answers (3 PII items → 0)
- **Chunking strategy matters** — 7 strategies, no single best one, depends on document type
- **Metadata filtering** — exclude outdated/duplicate docs, filter by department and year
- **Deduplication saves money** — don't pay for embedding the same document twice
- **Summarization fits context** — compress long docs so they fit in LLM context window

## Architecture

```
rag-demo/
├── app.py                          — Streamlit UI (sidebar toggles, Q&A, metrics)
├── loader.py                       — PDF → text + metadata (department, year, version)
├── preprocessing/
│   ├── __init__.py                 — re-exports
│   ├── pii.py                      — 7 regex patterns (email, phone, SSN, card, DOB, MRN, insurance)
│   ├── dedup.py                    — SHA-256 exact + SequenceMatcher fuzzy dedup
│   ├── summarize.py                — GPT-4o-mini for docs > 3000 chars
│   └── chunking.py                 — 7 chunking strategies
├── rag/
│   ├── __init__.py                 — re-exports
│   ├── embeddings.py               — OpenAI text-embedding-3-small (TF-IDF fallback)
│   ├── search.py                   — cosine similarity top-K retrieval
│   └── generation.py               — GPT-4o-mini answer generation
├── quality.py                      — quality score + PII leak detection in answer
└── docs/                           — 18 PDF healthcare documents
```

## Pipeline Flow

```
18 PDF docs → loader.py → metadata extraction
                  ↓
             Metadata Filters (year, department, version)
                  ↓
             PII Redaction → Dedup → Summarize → Chunking
                  ↓
             Embed (OpenAI) → Search (cosine) → GPT Answer
                  ↓
             Quality check (PII leak detection)
```

## Quick Start

```bash
# 1. Install dependencies
pip install streamlit pdfplumber openai python-dotenv scikit-learn langchain-text-splitters

# 2. Set your OpenAI key in .env (in parent directory)
echo "OPENAI_KEY=sk-your-key" > ../.env

# 3. Run
streamlit run app.py
```

Open http://localhost:8501.

## Demo Flow (for lecture)

1. Click "Load sample clinic data" — loads 18 PDFs
2. All preprocessing OFF → ask "How do I schedule a cardiology appointment?"
3. GPT answers with real patient emails and phones → **HIPAA violation**
4. Turn ON "PII Redaction" → PII items in answer: 3 → 0
5. Turn ON "Deduplication" → removes 3 duplicate docs (18 → 15)
6. Turn ON "Exclude outdated/duplicate" → removes policy_2022, keeps only 2024
7. Try different chunking strategies → see how retrieval quality changes

## Preprocessing Steps

| Step | What it does | Impact |
|------|-------------|--------|
| PII Redaction | Replaces email, phone, SSN, card, DOB, MRN, insurance ID with placeholders | 3 PII leaked → 0 |
| Deduplication | SHA-256 exact + SequenceMatcher fuzzy (threshold 0.7) | 18 docs → 15 unique |
| Summarization | GPT-4o-mini compresses docs > 3000 chars to 30-50% | Fits long docs in context |
| Chunking | 7 strategies: fixed, recursive, semantic, parent-child, context-enriched, by-section, none | Affects retrieval quality |
| Metadata Filters | Filter by year, department, exclude outdated/duplicate | Only relevant docs in RAG |

## Chunking Strategies

| Strategy | How it works | Best for |
|----------|-------------|----------|
| No chunking | Whole document as one chunk | Short documents |
| Fixed-size | Split by N chars, space separator | Simplest, but cuts sentences |
| Recursive character | Split by `\n\n` → `\n` → `. ` → ` ` | Universal default |
| Semantic | Embedding similarity between sentences, split at low similarity | Thematically diverse docs |
| Parent-child | Large chunks (3x) with small sub-chunks, search sub, return parent | Need both precision and context |
| Context-enriched | Recursive split + prepend document title to each chunk | Chunks that are unclear without context |
| By section | Split at UPPERCASE headers, then recursive within sections | Structured docs (protocols, policies) |

## Documents (docs/)

18 healthcare PDFs including:

- 8 patient scheduling inquiries (with duplicates for dedup testing)
- Billing inquiry, insurance verification
- Lab results, prescription refill
- Scheduling policies (2022 outdated + 2024 current — for metadata filtering)
- Compliance handbook, urgent care protocol
- Staff meeting notes
