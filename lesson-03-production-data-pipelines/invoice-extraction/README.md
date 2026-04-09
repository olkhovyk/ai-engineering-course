# Invoice Extraction — Hybrid Pipeline

Streamlit app that extracts structured data from PDF invoices using two approaches side-by-side: LLM-only vs Hybrid (Regex + LLM).

Shows that not everything needs to go through an LLM — regex is free, and preprocessing the text before sending to GPT saves 24-28% tokens on structured invoices.

## What This Project Demonstrates

- **Rule-based before LLM** — extract what you can with regex (free), send only the rest to GPT (paid)
- **Cost optimization** — strip already-found values from text + minimize schema → fewer tokens
- **Graceful degradation** — clean invoices: regex handles 90%, savings 28%. OCR scans: regex handles 20%, LLM does the rest. System never breaks, just costs more on bad data
- **Data quality determines ROI** — preprocessing saves more on clean data than on dirty data

## Architecture

```
invoice-extraction/
├── app.py                  — Streamlit UI (side-by-side comparison, metrics)
├── loader.py               — PDF → text (pdfplumber), list invoices
├── regex_extractor.py      — 10 regex patterns for common invoice fields
├── llm_extractor.py        — two GPT-4o-mini modes (full text vs remaining only)
├── pipeline.py             — orchestrates: mode → regex → LLM → merged result
├── requirements.txt        — dependencies
└── invoices/               — 6 sample PDF invoices
```

## How Hybrid Mode Works

```
Step 1: Regex (free, instant)
    → finds 9/10 fields: invoice_number, date, total, tax, subtotal,
      payment_terms, due_date, currency, phone/email

Step 2: Optimize text for LLM
    → removes already-found values from text (shorter input)
    → builds minimal JSON schema (only missing fields)

Step 3: LLM (paid, only missing fields)
    → sends shortened text + minimal schema to GPT-4o-mini
    → gets: vendor_name, customer_name, line_items, notes

Step 4: Merge
    → regex results + LLM results = complete invoice
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your OpenAI key in .env (in parent directory)
echo "OPENAI_KEY=sk-your-key" > ../.env

# 3. Run
streamlit run app.py --server.port 8502
```

Open http://localhost:8502.

## Test Results (real OpenAI API)

| Invoice | Type | Regex found | LLM Only | Hybrid | Savings |
|---------|------|-------------|----------|--------|---------|
| clean | Well-structured | 9/10 fields | 870 tok | 645 tok | **26%** |
| messy | Bad formatting | 9/10 fields | 804 tok | 577 tok | **28%** |
| foreign | Spanish language | 8/10 fields | 814 tok | 615 tok | **24%** |
| OCR scan | Scanned, artifacts | 2/10 fields | 784 tok | 738 tok | 6% |
| minimal | Almost empty | 3/10 fields | 573 tok | 506 tok | 12% |
| multi-page | 2 pages, many items | 7/10 fields | 1653 tok | 1603 tok | 3% |

## Regex Patterns

10 patterns in `regex_extractor.py`:

| Field | Pattern examples |
|-------|-----------------|
| invoice_number | `INV-XXXX`, `#XXXX` |
| date | `January 15, 2024`, `01/15/2024` |
| total | `$11,879.84` |
| subtotal | `Subtotal: $X,XXX.XX` |
| tax | `Tax: $XXX.XX` |
| payment_terms | `Net 30`, `Due on receipt` |
| due_date | `Due: February 14, 2024` |
| currency | `USD`, `EUR`, `$` |
| phone | `(555) 123-4567` |
| email | `billing@company.com` |

## Sample Invoices (invoices/)

| File | Purpose |
|------|---------|
| `invoice_clean.pdf` | Ideal formatting, baseline |
| `invoice_messy.pdf` | Poor formatting, inconsistent spacing |
| `invoice_foreign.pdf` | Spanish language invoice |
| `invoice_ocr_scan.pdf` | Scanned document with OCR artifacts |
| `invoice_multi_page.pdf` | 2 pages, multiple line items |
| `invoice_minimal.pdf` | Almost empty, minimal info |

## At Scale

10,000 invoices/month with hybrid mode:

- Structured invoices (70%): 25% token savings
- Unstructured (30%): 5% savings
- **Total: ~$50-100/month saved** on OpenAI tokens alone
