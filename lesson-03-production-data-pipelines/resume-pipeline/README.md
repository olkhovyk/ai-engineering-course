# Resume Pipeline

**Flow:** PDF resumes → Extract → Preprocess (clean + PII redact) → Score with LLM

Two ways to run: standalone Python script or full Airflow orchestration.

## Quick Start (standalone — no Airflow)

```bash
# 1. Run full pipeline
python dags/resume_dag.py

# 2. View analytics in DuckDB
python run_dbt.py
```

## Airflow Mode (Docker)

```bash
# 1. Set your OpenAI key
cp .env.example .env
# edit .env → OPENAI_KEY=sk-your-key

# 2. Start Airflow
docker compose up -d

# 3. Wait ~30 sec, open UI
open http://localhost:8080
# Login: admin / admin

# 4. Find "resume_processing_pipeline" DAG → trigger it

# 5. Stop when done
docker compose down
```

### What you see in Airflow UI:
- **DAG graph**: `extract_resumes → preprocess_resumes → score_with_llm`
- **Each task**: green (success), red (failed), yellow (running)
- **Logs**: click any task → Log → see full output
- **Retry**: if a task fails, Airflow retries 2 times automatically

## Structure

```
resume-pipeline/
├── dags/
│   └── resume_dag.py           # Airflow DAG (works standalone too)
├── scripts/
│   └── extract.py              # PDF → clean text + PII redaction
├── score.py                    # LLM scoring (GPT-4o-mini)
├── run_dbt.py                  # DuckDB analytics (staging → mart)
├── dbt_project/
│   └── models/
│       ├── stg_resumes.sql     # Raw staging
│       └── mart_resumes.sql    # Scored + enriched
├── data/
│   └── resumes/                # 6 sample PDFs
├── docker-compose.yml          # Airflow + Postgres
├── requirements.txt            # Local dependencies
├── requirements-airflow.txt    # Dependencies inside Docker
└── .env.example
```

## Sample Resumes

| File | Problem | PII Count |
|------|---------|-----------|
| `01_clean_resume.pdf` | None (baseline) | 2 |
| `02_dirty_encoding_resume.pdf` | Smart quotes, boilerplate | 2 |
| `03_pii_heavy_resume.pdf` | SSN, DOB, address, salary, references | **15** |
| `04_very_long_resume.pdf` | Verbose (5 pages worth) | 9 |
| `05_noisy_boilerplate_resume.pdf` | ATS system headers/metadata | 4 |
| `06_minimal_resume.pdf` | Too little info | 1 |

## Why Airflow?

Without Airflow (script): run manually, no retry, no monitoring.

With Airflow:
- **Schedule**: run every day at 6am automatically
- **Retry**: if OpenAI API times out → retry 2x with 2min delay
- **Monitoring**: UI shows which step failed and why
- **Alerting**: Slack/email when pipeline breaks
- **History**: see all past runs, duration, success rate
