# Звіт: LLM Fine-Tuning in Production

## Що вимірювалося

Я перевіряв, чи може fine-tuned Llama 3.1 8B краще витягувати структурований JSON з customer support emails, ніж та сама 8B модель без fine-tuning.

Eval set складався з 30 прикладів, включно з edge cases: anonymous sender, multiple issues, sarcasm, implicit urgency, короткі повідомлення і mixed-language email. Training set містив 300 синтетичних прикладів. Перед training був виконаний hash-check: overlap між train і eval дорівнює 0.

## Метрики

| Metric                   | Base 8B | Fine-tuned 8B |
|--------------------------|---------|---------------|
| json_valid_rate          | 0.0%    | 100.0%        |
| exact_match_rate         | 0.0%    | 66.7%         |
| field.customer_name      | 0.0%    | 93.3%         |
| field.product            | 0.0%    | 93.3%         |
| field.issue_category     | 0.0%    | 90.0%         |
| field.urgency            | 0.0%    | 90.0%         |
| field.summary            | 0.0%    | 76.7%         |
| avg_input_tokens         | 99.07   | 99.07         |
| avg_output_tokens        | 220.00  | 41.70         |
| latency_p50_sec          | 13.46   | 2.85          |
| latency_p95_sec          | 19.57   | 3.55          |

## Що вийшло

Найбільший lift був у форматі відповіді. Base 8B не повертав валідний JSON на eval set, тому `json_valid_rate` і всі field accuracy були 0%. Після QLoRA fine-tuning модель почала стабільно відповідати саме в потрібному JSON schema: `json_valid_rate` став 100%.

Також сильно покращилась ефективність inference. Fine-tuned model генерує в середньому 41.7 output tokens замість 220, тому latency p50 зменшилась з 13.46 сек до 2.85 сек. Це логічно: модель навчилась одразу писати короткий структурований JSON, а не довгу або нерелевантну відповідь.

Найкраще працюють поля `customer_name` і `product` — по 93.3%. Поля `issue_category` і `urgency` теж стали сильними — по 90.0%. Найскладніше поле — `summary`, там 76.7%, бо це не exact classification, а коротке natural language summary, де більше варіативності.

## Що не вийшло

Дані все ще маленькі: 300 training examples і 30 eval examples — це достатньо для навчальної перевірки гіпотези, але мало для production-рішення. Через це є ризик overfitting: модель могла добре вивчити стиль синтетичних прикладів, але гірше поводитися на реальних customer emails.

Є ризик train/serve skew: training data синтетична, а production emails можуть мати інший стиль, довжину, шум, HTML, forwarding chains, signatures і вкладення. Також можлива проблема catastrophic forgetting, якщо adapter занадто сильно привчає модель до одного формату і погіршує загальну поведінку поза цією задачею.

Base 8B у цьому запуску був дуже слабким саме по JSON-following. Це робить lift великим, але також означає, що порівняння треба трактувати обережно: сильніший prompt або instruct checkpoint міг би дати кращий baseline.

## Cost & breakeven

Training cost у цьому експерименті дорівнює $0, бо fine-tuning запускався в Google Colab free на T4. Реальна ціна в production буде не в training, а в inference та maintenance.

Fine-tuned 8B має p50 latency 2.85 сек на T4 і генерує значно менше токенів. Якщо компанія обробляє 50К emails/день, self-hosted 8B може бути вигідним, коли:

- traffic стабільний і великий;
- потрібен контроль над latency та privacy;
- задача вузька і добре описується schema;
- API-вартість на великих моделях стає постійною операційною витратою.

Якщо traffic малий або якість API-моделі суттєво краща, дешевше залишитися на API. Якщо traffic великий, а fine-tuned 8B дає достатню якість, self-hosting або dedicated inference endpoint має сенс.

## Бізнес-рекомендація

Fine-tuning у цьому випадку має сенс, бо задача вузька, повторювана і має чіткий JSON schema. Fine-tuned 8B значно краще тримає формат, дає високу accuracy по важливих полях і працює швидше за base 8B у цьому експерименті. Для production я б не запускав це одразу на всіх 50К emails/день, а спочатку зробив би shadow mode на реальних листах, розширив eval set до 300-500 прикладів і окремо перевірив critical/urgency помилки. Якщо на реальних даних urgency accuracy залишиться близько 90% або вище, fine-tuned 8B можна розглядати як production-кандидата.
