# Enterprise Document Challenges & Solutions

Real-world document ingestion is nothing like processing clean sample files. This guide covers the most common enterprise challenges and how our pipeline handles them.

---

## Challenge 1: Corrupted / Truncated Files

**Problem**: Files get corrupted during transfer, partial downloads, storage failures.
Truncated PDFs miss `%%EOF`, broken DOCX files have invalid ZIP structure.

**Symptoms**: Parser crashes with `PdfReadError`, `BadZipFile`, or hangs indefinitely.

**Solution**:
- `FileValidator` checks file size > 0 before parsing
- `retry_with_backoff()` retries on transient I/O errors
- `DeadLetterQueue` quarantines unfixable files with error reports
- **Code**: `src/ingestion/resilience.py:FileValidator`

---

## Challenge 2: Scanned PDFs (Image-Only, No Text Layer)

**Problem**: Legal docs, old contracts, faxes — saved as PDFs but contain only rasterized images. `PyPDF2.extract_text()` returns empty string.

**Symptoms**: Parsed text is empty or below threshold (< 50 chars).

**Solution**:
- `PDFParser` checks text length against `min_text_length` threshold
- Falls back to OCR via `pytesseract` + `pdf2image`
- Marks result with `ocr_applied=True` for downstream awareness
- **Code**: `src/parsers/pdf_parser.py:_extract_with_ocr()`

---

## Challenge 3: Empty Files (0 Bytes)

**Problem**: Failed exports, placeholder files, `touch`-created files, sync conflicts.

**Symptoms**: Parser crashes on empty input, or silently produces empty output.

**Solution**:
- `FileValidator` rejects 0-byte files immediately
- Clear error message: "File is empty. Check the source system for export errors."
- **Code**: `src/ingestion/resilience.py:FileValidator.validate()`

---

## Challenge 4: Wrong File Extensions

**Problem**: HTML saved as `.pdf`, PDF saved as `.html`. Caused by CMS bugs, user error, email corruption.

**Symptoms**: Parser for declared type crashes on unexpected content.

**Solution**:
- `FileValidator` detects real type via **magic bytes** (file header signatures)
- Reports mismatch: "extension is .pdf but content looks like html"
- Pipeline can optionally route to correct parser based on detected type
- **Code**: `src/ingestion/resilience.py:MAGIC_SIGNATURES`, `FileValidator._detect_type()`

---

## Challenge 5: Encoding Nightmares

**Problem**: Legacy systems produce Windows-1251, Latin-1, Shift-JIS without declaring encoding. UTF-8 BOM markers confuse naive readers. Mixed encodings in a single corpus.

**Symptoms**: `UnicodeDecodeError`, mojibake (Ð¿ÑÐ¸Ð²ÑÑ), garbled text.

**Solution**:
- `EncodingNormalizer` tries 9 encodings in priority order
- Strips UTF-8 BOM automatically
- Heuristic: skip encodings that produce > 1% replacement chars
- Last resort: `utf-8` with `errors="replace"`
- **Code**: `src/ingestion/resilience.py:EncodingNormalizer`

---

## Challenge 6: Malformed / Deeply Nested HTML

**Problem**: Word-exported HTML has 50+ levels of nesting, unclosed tags, broken entities, inline styles everywhere. SharePoint / CMS HTML is bloated.

**Symptoms**: Parser is slow, extracted text has style/class noise, broken structure.

**Solution**:
- BeautifulSoup with `lxml` parser handles malformed HTML gracefully
- Scripts and styles are stripped via `tag.decompose()`
- `get_text(separator="\n", strip=True)` extracts clean text regardless of nesting
- **Code**: `src/parsers/html_parser.py`

---

## Challenge 7: Boilerplate-Heavy Pages (Low Signal-to-Noise)

**Problem**: Navigation, sidebars, footers, cookie banners, analytics scripts — actual content is 5% of the HTML.

**Symptoms**: Chunks are full of navigation items and boilerplate, not actual content.

**Solution**:
- Strip `<script>`, `<style>` tags (already handled)
- For production: consider **readability algorithms** (like Mozilla Readability) or **main content extraction** (trafilatura library)
- Chunking with `paragraph` strategy naturally filters short boilerplate items
- **Future improvement**: add content density scoring per HTML section

---

## Challenge 8: Password-Protected / Encrypted PDFs

**Problem**: HR docs, financial reports, legal contracts. PDF has `/Encrypt` dictionary.

**Symptoms**: `PyPDF2` raises `PdfReadError: File has not been decrypted`.

**Solution**:
- `ResilientParser` catches the error and classifies as `FATAL`
- Quarantines with suggestion: "File is password-protected. Obtain the password or request an unprotected version."
- For known passwords: `PdfReader` supports `reader.decrypt(password)`
- **Code**: `src/ingestion/resilience.py:ResilientParser._classify_error()`

---

## Challenge 9: Huge Files (Memory Pressure)

**Problem**: Auto-generated logs, database exports, audit trails — 100K+ row HTML tables, 500+ page PDFs.

**Symptoms**: OOM errors, slow processing, pipeline bottleneck.

**Solution**:
- `FileValidator` has configurable `max_size_mb` limit
- For production: implement **streaming parsers** that process page-by-page
- Batcher controls how many documents are processed concurrently
- **Code**: `src/ingestion/resilience.py:FileValidator`, `src/streaming/batcher.py`

---

## Challenge 10: Mixed-Language Documents

**Problem**: Multinational orgs, UN/EU docs, multilingual reports. Multiple scripts (Latin, Cyrillic, CJK, Arabic RTL).

**Symptoms**: Tokenization breaks, chunking splits mid-word in CJK, language detection fails.

**Solution**:
- UTF-8 encoding handles all scripts natively
- Sentence-based chunking (`strategy="sentence"`) respects sentence boundaries across languages
- For production: add language detection per chunk (e.g., `langdetect` library) and route to language-specific models
- **Code**: `src/ingestion/chunker.py:Chunker._sentence()`

---

## Challenge 11: Broken DOCX Archives

**Problem**: DOCX is a ZIP file. Corruption during email, sync, or storage breaks the ZIP structure. Missing `word/document.xml`.

**Symptoms**: `BadZipFile`, `KeyError: 'word/document.xml'`.

**Solution**:
- `FileValidator` detects ZIP magic bytes (`PK\x03\x04`)
- `ResilientParser` catches `BadZipFile` and quarantines
- Suggestion: "File is corrupted. Request a fresh copy from the source system."
- **Code**: `src/ingestion/resilience.py:ResilientParser.safe_parse()`

---

## Challenge 12: Binary Garbage

**Problem**: Random binary data with document extension. Database dumps, compiled files, images renamed.

**Symptoms**: Parser crashes with codec errors, segfaults, or produces meaningless output.

**Solution**:
- `FileValidator` checks magic bytes — random data won't match any known signature
- If parsing fails, `ResilientParser` quarantines with clear error
- **Code**: `src/ingestion/resilience.py:FileValidator._detect_type()`

---

## Architecture Summary

```
File arrives
    │
    ▼
[FileValidator] ─── empty? too large? wrong type?
    │                        │
    │ OK                     ▼ FAIL
    ▼                   [DeadLetterQueue]
[Parser Router]              │
    │                        ▼
    │ parse error?      error_report.json
    ▼     │
[retry_with_backoff]
    │     │
    │     ▼ exhausted
    │  [DeadLetterQueue]
    ▼
[Chunker]
    │
    ▼
[VersionStore] ─── snapshot for reproducibility
```

## Running the Enterprise Challenge

```bash
# 1. Generate bad documents
python src/generate_bad_samples.py

# 2. Run pipeline in resilient mode
python src/main.py --input samples/enterprise_challenges --resilient

# 3. Check quarantine
ls data/quarantine/

# 4. Review error reports
cat data/quarantine/*_error.json
```
