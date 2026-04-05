-- Mart: scored and enriched resumes ready for analysis
-- Joins preprocessing metrics with LLM scores

WITH staged AS (
    SELECT * FROM {{ ref('stg_resumes') }}
),

scores AS (
    SELECT
        file                            AS resume_file,
        score->>'score'                 AS llm_score,
        score->>'recommendation'        AS recommendation,
        score->>'reasoning'             AS reasoning,
        pii_total                       AS original_pii_count
    FROM {{ source('raw', 'scored_resumes') }}
)

SELECT
    s.resume_file,
    s.raw_char_count,
    s.processed_char_count,
    s.compression_ratio,
    s.pii_items_found,
    CAST(sc.llm_score AS INTEGER)       AS score,
    sc.recommendation,
    sc.reasoning,
    -- Derived metrics
    CASE
        WHEN s.pii_items_found > 5 THEN 'HIGH_RISK'
        WHEN s.pii_items_found > 0 THEN 'MEDIUM_RISK'
        ELSE 'CLEAN'
    END                                 AS pii_risk_level,
    CASE
        WHEN s.compression_ratio < 0.7 THEN 'HEAVILY_CLEANED'
        WHEN s.compression_ratio < 0.9 THEN 'MODERATELY_CLEANED'
        ELSE 'MINIMAL_CHANGES'
    END                                 AS cleaning_impact,
    s.loaded_at
FROM staged s
LEFT JOIN scores sc ON s.resume_file = sc.resume_file
ORDER BY CAST(sc.llm_score AS INTEGER) DESC NULLS LAST
