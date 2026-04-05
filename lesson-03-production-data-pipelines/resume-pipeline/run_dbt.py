"""
Runs dbt transformations on resume pipeline data.

Executes dbt models (staging → mart) using DuckDB adapter,
then queries the results to display analytics.

Prerequisites:
  pip install dbt-duckdb
  python dags/resume_dag.py   # generate JSON data first
"""

import subprocess
import sys
from pathlib import Path

import duckdb

DBT_DIR = Path(__file__).parent / "dbt_project"
DB_PATH = Path(__file__).parent / "data" / "resume_analytics.duckdb"


def run_dbt():
    """Run dbt models."""
    print("=" * 65)
    print("Running dbt models...")
    print("=" * 65)

    result = subprocess.run(
        ["dbt", "run", "--profiles-dir", "."],
        cwd=str(DBT_DIR),
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print("dbt STDERR:", result.stderr)
        sys.exit(1)


def show_results():
    """Query dbt-created tables and display analytics."""
    con = duckdb.connect(str(DB_PATH), read_only=True)

    print("=" * 65)
    print("STAGING: stg_resumes")
    print("=" * 65)
    df = con.execute("""
        SELECT resume_file, raw_char_count, processed_char_count,
               pii_items_found, compression_ratio
        FROM stg_resumes
    """).fetchdf()
    print(df.to_string(index=False))

    print(f"\n{'=' * 65}")
    print("MART: mart_resumes")
    print("=" * 65)
    df = con.execute("""
        SELECT resume_file, score, recommendation,
               pii_risk_level, cleaning_impact
        FROM mart_resumes
    """).fetchdf()
    print(df.to_string(index=False))

    print(f"\n{'=' * 65}")
    print("SUMMARY")
    print("=" * 65)
    summary = con.execute("""
        SELECT
            COUNT(*)                                    AS total_resumes,
            AVG(score)                                  AS avg_score,
            SUM(CASE WHEN pii_risk_level = 'HIGH_RISK'
                     THEN 1 ELSE 0 END)                 AS high_risk_count,
            SUM(CASE WHEN recommendation IN ('yes', 'strong_yes')
                     THEN 1 ELSE 0 END)                 AS recommended
        FROM mart_resumes
    """).fetchdf()
    print(summary.to_string(index=False))

    con.close()


if __name__ == "__main__":
    data_dir = Path(__file__).parent / "data"
    if not (data_dir / "preprocessed_resumes.json").exists():
        print("Run 'python dags/resume_dag.py' first to generate data.")
        sys.exit(1)

    run_dbt()
    show_results()
