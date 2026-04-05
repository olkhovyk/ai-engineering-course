-- Staging: raw extracted resume data
-- Source: JSON output from extract.py

SELECT
    file                    AS resume_file,
    raw_length              AS raw_char_count,
    clean_length            AS clean_char_count,
    processed_length        AS processed_char_count,
    compression_ratio,
    pii_total               AS pii_items_found,
    sections_detected,
    text                    AS resume_text,
    CURRENT_TIMESTAMP       AS loaded_at
FROM {{ source('raw', 'preprocessed_resumes') }}
