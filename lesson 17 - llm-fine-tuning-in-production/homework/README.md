# Домашнє завдання 17: LLM Fine-Tuning in Production

Це домашнє завдання про fine-tuning LLM у production-підході: спочатку фіксуємо eval set, потім міряємо baseline, потім робимо QLoRA fine-tuning і тільки після цього порівнюємо метрики.

## Бізнес-контекст

Уявімо SaaS-компанію з великим потоком support emails. Потрібно автоматично перетворювати кожен email на JSON для CRM.

Модель має витягнути:

- хто пише;
- продукт;
- категорію звернення;
- urgency;
- коротке резюме.

Це потрібно, щоб швидко роутити critical incidents, знаходити billing-проблеми і скорочувати time-to-first-response.

## Формат відповіді моделі

На вході модель отримує email:

```text
Hi, I was charged twice for Starter Plan this month. My card shows two charges of $29.99 on the same day. Please refund the duplicate. - Anna
```

На виході має бути тільки валідний JSON:

```json
{
  "customer_name": "Anna",
  "product": "Starter Plan",
  "issue_category": "billing",
  "urgency": "high",
  "summary": "Duplicate charge for Starter Plan, refund requested"
}
```

## Структура проєкту

```text
homework/
  data/
    train.jsonl
    eval.jsonl
  results/
    base_8b_metrics.json
    finetuned_8b_metrics.json
  scripts/
    generate_data.py
    check_overlap.py
    compare_results.py
  notebooks/
    finetune_llama_3_1_8b_unsloth_colab.ipynb
  requirements.txt
  README.md
  REPORT.md
```

## Дані

`data/eval.jsonl` містить 30 eval-прикладів. Вони потрібні для чесної перевірки якості і мають бути створені до fine-tuning.

`data/train.jsonl` містить training set у chat format. Його можна використовувати для supervised fine-tuning.

Eval set включає edge cases:

- anonymous або неповне ім'я;
- кілька проблем в одному email;
- sarcasm / passive aggressive tone;
- implicit urgency;
- короткі або змішаномовні повідомлення.

## Локальна перевірка даних

Локальні helper scripts не потребують зовнішніх пакетів.

Перегенерувати дані:

```powershell
python scripts/generate_data.py
```

Перевірити, що `train.jsonl` не перетинається з `eval.jsonl`:

```powershell
python scripts/check_overlap.py
```

Очікуваний результат:

```text
train examples: 300
eval examples: 30
overlap: 0
OK: train/eval overlap not found
```

## Baseline

За умовами завдання baseline треба робити на `Llama 3.1 8B base` без fine-tuning.

Запуск baseline відбувається у Google Colab.

Notebook:

```text
notebooks/finetune_llama_3_1_8b_unsloth_colab.ipynb
```

Потрібно зберегти результат у:

```text
results/base_8b_metrics.json
```

Метрики:

- `json_valid_rate`
- `exact_match_rate`
- `field_accuracy.customer_name`
- `field_accuracy.product`
- `field_accuracy.issue_category`
- `field_accuracy.urgency`
- `field_accuracy.summary`
- input/output tokens або приблизна оцінка tokens
- latency на T4

## Fine-tuning

Fine-tuning виконується у Google Colab через Unsloth + QLoRA.

Параметри з умови:

- model: `Llama 3.1 8B`
- quantization: 4-bit
- LoRA rank: `r=16`
- LoRA alpha: `32`
- epochs: `3`
- GPU: Colab free T4

Після навчання треба зберегти adapter weights. Очікуваний розмір adapter-а приблизно десятки MB.

## Re-evaluate

Після fine-tuning треба прогнати ту саму `data/eval.jsonl` на fine-tuned model.

Результат зберегти у:

```text
results/finetuned_8b_metrics.json
```

Важливо: eval set має бути той самий, що і для baseline. Інакше comparison буде нечесний.

## Порівняння результатів

Після Colab треба покласти два файли в `results/`:

```text
results/base_8b_metrics.json
results/finetuned_8b_metrics.json
```

Після цього локально можна згенерувати markdown-таблицю:

```powershell
python scripts/compare_results.py
```

## Що має бути у фінальному звіті

У фінальному README або окремому report треба показати:

1. Comparison table: base 8B vs fine-tuned 8B.
2. `json_valid_rate`.
3. `exact_match_rate`.
4. Accuracy по 5 полях.
5. Tokens / latency.
6. Cost & breakeven:
   - training cost: $0, якщо Colab free;
   - inference latency на T4;
   - коли self-hosting має сенс проти API.
7. Що вийшло:
   - де був найбільший lift;
   - чому саме там.
8. Що не вийшло:
   - мало даних;
   - overfitting;
   - train/serve skew;
   - catastrophic forgetting;
   - base 8B already close to ceiling;
   - OOM на T4;
   - Colab disconnect.
9. Бізнес-рекомендація на 3-5 речень.

## Поточний статус

Підготовлено:

- synthetic train set;
- eval set з edge cases;
- hash overlap checker.
- Colab notebook для baseline + QLoRA fine-tuning + re-eval.
- comparison helper для результатів.
- результати baseline і fine-tuned eval.
- фінальний звіт у `REPORT.md`.

Згенеровані артефакти:

- `results/base_8b_metrics.json`
- `results/finetuned_8b_metrics.json`
- `REPORT.md`
