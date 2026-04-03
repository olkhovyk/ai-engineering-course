Завантажую функції з homework.ipynb...

Файли для роботи:
  actually_html.pdf                                99 bytes
  actually_pdf.html                                68 bytes
  binary_garbage.pdf                            1,024 bytes
  boilerplate_heavy.html                        5,448 bytes
  broken_archive.docx                           4,400 bytes
  complex_merged_formulas.xlsx                  9,275 bytes
  corrupted.xlsx                                5,100 bytes
  corrupted_truncated.pdf                         352 bytes
  empty_file.docx                                   0 bytes
  empty_file.html                                   0 bytes
  empty_file.pdf                                    0 bytes
  empty_with_headers.xlsx                       4,862 bytes
  financial_report_table.pdf                    2,857 bytes
  huge_audit_log.txt                        1,360,996 bytes
  huge_export.xlsx                            410,512 bytes
  huge_repetitive.html                      1,004,477 bytes
  latin1_mixed.html                               135 bytes
  malformed_deeply_nested.html                  1,490 bytes
  multilingual.html                             1,252 bytes
  normal_report.xlsx                            5,623 bytes
  password_protected.pdf                          602 bytes
  scanned_no_text.pdf                           1,010 bytes
  unicode_data.xlsx                             5,400 bytes
  utf8_with_bom.html                              194 bytes
  windows1251_no_charset.html                     167 bytes
utf8_with_bom.html:
  Кодування: utf_8
  BOM: True
  Перші 150 символів: <html><head><meta charset="utf-8"><title>BOM Test</title></head><body><p>This file has a UTF-8 BOM marker.</p><p>Деякі символи українською мовою.</p><

windows1251_no_charset.html:
  Кодування: cp1251
  BOM: False
  Перші 150 символів: <html><head><title>Звіт</title></head><body><p>Цей документ в кодуванні Windows-1251 без мета-тегу charset.</p><p>Типова проблема з legacy системами.<

latin1_mixed.html:
  Кодування: cp1250
  BOM: False
  Перші 150 символів: <html><head><title>Rapport</title></head><body><p>Geräteübersicht und Maßnahmen.</p><p>Résumé des résultats français.</p></body></html>

  [MISMATCH] actually_html.pdf: declared=.pdf, real=html
          -> Type mismatch
  [MISMATCH] actually_pdf.html: declared=.html, real=pdf
          -> Type mismatch
  [OK] binary_garbage.pdf: declared=.pdf, real=None
  [OK] empty_file.pdf: declared=.pdf, real=None
          -> empty file
  [OK] normal_report.xlsx: declared=.xlsx, real=xlsx
malformed_deeply_nested.html:
  HTML: 1,461 символів -> Текст: 282 символів
  Корисність: 19.3%
  Текст: Enterprise Report Q4
Important quarterly data buried under 50 levels of nesting.
Revenue increased by 15% year-over-year.
Metric
Value
Revenue
$1.2M
Users
45,000
Profit & Loss for Q4 — results are © c...

boilerplate_heavy.html:
  HTML: 5,342 символів -> Текст: 635 символів
  Корисність: 11.9%
  Текст: Company Intranet - Important Policy Update
Important Policy Update: Data Handling Procedures
Effective March 1, 2026, all departments must follow updated data handling
                procedures for p...

multilingual.html:
  HTML: 885 символів -> Текст: 675 символів
  Корисність: 76.3%
  Текст: Multilingual Report
Quarterly Report / Щоквартальний звіт / 四半期報告
English
Revenue grew by 12% in Q4 2025, driven primarily by expansion into
new markets in Southeast Asia and Eastern Europe.
Українськ...

libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
Warning: No languages specified, defaulting to English.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
Warning: No languages specified, defaulting to English.
Warning: No languages specified, defaulting to English.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
Warning: No languages specified, defaulting to English.
Warning: No languages specified, defaulting to English.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
=== Результати: 14 OK, 11 ERROR ===

OK:
  boilerplate_heavy.html: 528 символів
  complex_merged_formulas.xlsx: 4996 символів
  empty_with_headers.xlsx: 25 символів
  financial_report_table.pdf: 704 символів
  huge_audit_log.txt: 1345999 символів
  huge_export.xlsx: 722153 символів
  huge_repetitive.html: 494324 символів
  latin1_mixed.html: 61 символів
  malformed_deeply_nested.html: 264 символів
  multilingual.html: 655 символів
  normal_report.xlsx: 310 символів
  unicode_data.xlsx: 325 символів
  utf8_with_bom.html: 66 символів
  windows1251_no_charset.html: 96 символів

ERROR:
  actually_html.pdf: [type_mismatch] The file is type mismatched
  actually_pdf.html: [type_mismatch] The file is type mismatched
  binary_garbage.pdf: [parse_error] The file is corrupted
  broken_archive.docx: [type_mismatch] The file is type mismatched
  corrupted.xlsx: [type_mismatch] The file is type mismatched
  corrupted_truncated.pdf: [parse_error] The file is corrupted
  empty_file.docx: [empty] The file is completely empty (0 bytes).
  empty_file.html: [empty] The file is completely empty (0 bytes).
  empty_file.pdf: [empty] The file is completely empty (0 bytes).
  password_protected.pdf: [parse_error] The file is corrupted
  scanned_no_text.pdf: [parse_error] The file is corrupted
pdfplumber знайшов 2 таблиць

=== Таблиця 1: 5 рядків ===
  Колонки: ['Region', 'Q1', 'Q2', 'Q3', 'Q4', 'Total']
  {'Region': 'North America', 'Q1': '1,200,000', 'Q2': '1,350,000', 'Q3': '1,100,000', 'Q4': '1,500,000', 'Total': '5,150,000'}
  {'Region': 'Europe', 'Q1': '800,000', 'Q2': '920,000', 'Q3': '870,000', 'Q4': '1,050,000', 'Total': '3,640,000'}
  {'Region': 'APAC', 'Q1': '450,000', 'Q2': '520,000', 'Q3': '610,000', 'Q4': '780,000', 'Total': '2,360,000'}
  ... ще 2 рядків

=== Таблиця 2: 4 рядків ===
  Колонки: ['Product', 'Units Sold', 'Revenue', 'Avg Price', 'Margin %']
  {'Product': 'Enterprise Platform', 'Units Sold': '145', 'Revenue': '4,350,000', 'Avg Price': '30,000', 'Margin %': '72%'}
  {'Product': 'SMB Suite', 'Units Sold': '1,230', 'Revenue': '3,690,000', 'Avg Price': '3,000', 'Margin %': '65%'}
  {'Product': 'API Access', 'Units Sold': '8,500', 'Revenue': '2,550,000', 'Avg Price': '300', 'Margin %': '88%'}
  ... ще 1 рядків

=== unstructured (для порівняння) ===
Warning: No languages specified, defaulting to English.
Q4 2025 Financial Report
Revenue breakdown by region and product line.
Table 1: Quarterly Revenue by Region (USD)
Region
Q1
Q2
Q3
North America
1,200,000
1,350,000
1,100,000
Europe
800,000
920,000
870,000
APAC
450,000
520,000
610,000
LATAM
200,000
230,000
250,000
Total
2,650,000
3,020,000
2,830,000
Table 2: Revenue by Product Line
Product
Units Sold
Revenue
Enterprise Platform
145
4,350,000
SMB Suite
1,230
3,690,000
API Access
8,500
2,550,000
Consulting
310
1,550,000
Note: All figures are unaudi

^ Бачите різницю? unstructured втрачає структуру таблиці.
Файл: huge_audit_log.txt
Розмір: 1.30 MB, 1,350,998 символів
C:\Users\ilya1\Documents\rd_projects\ai-engineering-course\lesson-02-data-engineering\homework\.venv\Lib\site-packages\langchain_core\_api\deprecation.py:25: UserWarning: Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.
  from pydantic.v1.fields import FieldInfo as FieldInfoV1
Текст: 1,350,998 символів

  chunk_size |   чанків | сер. довж. |   час (мс)
----------------------------------------------------
         256 |     9000 |        170 |       67.1
         512 |     4000 |        336 |        3.6
        1024 |     1667 |        808 |        2.8
        2048 |      715 |       1888 |        3.6
chunk_size=512, текст: 1,350,998 символів

     overlap |   чанків |    додатково |   час (мс)
----------------------------------------------------
           0 |     4000 | +         0 |        3.4
          50 |     4000 | +         0 |        3.0
         100 |     4000 | +         0 |        2.8
         200 |     4000 | +         0 |        3.1

(overlap збільшує кількість чанків, бо текст дублюється на стиках)
Всього чанків: 4000

=== Чанк 0 (останні 150 символів) ===
...ear-over-year, driven by expansion into Southeast Asian markets. Operating margins improved from 22% to 27%, reflecting cost optimization initiatives.

=== Чанк 1 (перші 150 символів) ===
[Entry 00002] Customer acquisition costs decreased by 12% while retention rates improved to 94%. The enterprise segment showed particularly strong per...

^ Бачите overlap? Кінець чанка 0 повторюється на початку чанка 1.
  Це потрібно щоб контекст не губився на стиках.
============================================================
ЗАВДАННЯ 1: Визначення кодування
============================================================
  [PASS] BOM виявлено (+4)
  [PASS] BOM прибрано з тексту (+4)
  [PASS] CP1251 декодовано без кракозябрів (+3)
  [PASS] Кодування визначено (+3)
  [PASS] Latin-1 декодовано (+3)
  [PASS] Кодування визначено (+3)

============================================================
ЗАВДАННЯ 2: Визначення типу файлу (magic bytes)
============================================================
  [PASS] HTML-as-PDF: mismatch виявлено (+2)
  [PASS] HTML-as-PDF: detected=html (+2)
  [PASS] PDF-as-HTML: mismatch виявлено (+2)
  [PASS] PDF-as-HTML: detected=pdf (+2)
  [PASS] Empty file: issue виявлено (+2)
  [PASS] Empty file: detected=None (+2)
  [PASS] Binary garbage: не впав, повернув результат (+4)
  [PASS] Normal xlsx: no mismatch (+4)

============================================================
ЗАВДАННЯ 3: Витягування тексту з брудного HTML
============================================================
  [PASS] Malformed: текст витягнуто (+3)
  [PASS] Malformed: є 'Revenue' (+2)
  [PASS] Malformed: немає style атрибутів (+3)
  [PASS] Boilerplate: текст витягнуто (+2)
  [PASS] Boilerplate: немає script/analytics (+3)
  [PASS] Boilerplate: useful_ratio < 50% (+3)
  [PASS] Multilingual: є Ukrainian (+2)
  [PASS] Multilingual: є Japanese (+2)

============================================================
ЗАВДАННЯ 4: Safe parser
============================================================
  [PASS] Empty file → error (+2)
  [PASS] Empty file → type=empty (+2)
  [PASS] Wrong ext → error (+2)
  [PASS] Wrong ext → type=type_mismatch (+2)
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
Warning: No languages specified, defaulting to English.
  [PASS] Binary garbage → не впав (+2)
  [PASS] Binary garbage → error status (+2)
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
  [PASS] Normal HTML → ok (+2)
  [PASS] Normal HTML → є текст (+2)
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
Warning: No languages specified, defaulting to English.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
Warning: No languages specified, defaulting to English.
Warning: No languages specified, defaulting to English.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
Warning: No languages specified, defaulting to English.
Warning: No languages specified, defaulting to English.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
libmagic is unavailable but assists in filetype detection. Please consider installing libmagic for better results.
  [PASS] Жоден файл не крашить функцію (crashed=0) (+4)

============================================================
ЗАВДАННЯ 5: Витягування таблиць з PDF
============================================================
  [PASS] Повертає list (+2)
  [PASS] Знайдено 2 таблиці (+3)
  [PASS] Таблиця 1: рядки — словники (+2)
  [PASS] Таблиця 1: є ключ 'Region' (+2)
  [PASS] Таблиця 1: 5 рядків даних (без заголовка) (+2)
  [PASS] Таблиця 1: North America Q1 = 1,200,000 (+3)
  [PASS] Таблиця 2: є ключ 'Product' (+2)
  [PASS] Таблиця 2: 4 рядки даних (+2)
  [PASS] Таблиця 2: Enterprise Platform revenue (+2)

============================================================
ЗАВДАННЯ 6: Chunking великого документа
============================================================
  [PASS] Повертає list (+2)
  [PASS] Чанків > 1 (+2)
  [PASS] Кожен чанк — рядок (+2)
  [PASS] Чанки <= chunk_size (+3)
  [PASS] chunk_size=256 дає більше чанків ніж 1024 (+3)
  [PASS] overlap=200 дає більше чанків ніж overlap=0 (+3)
  [PASS] Великий файл (1,350,998 chars) за < 5с (+3)

============================================================
РЕЗУЛЬТАТ: 118/118 балів (100%)
============================================================
Відмінно!