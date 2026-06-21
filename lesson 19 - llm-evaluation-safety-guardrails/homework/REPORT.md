# Звіт: LLM Evaluation, Safety & Guardrails

## Асистент

Для домашнього завдання я зробив простого customer support assistant. Він відповідає на питання користувачів на основі локального файлу `data/policy_docs.md`.

Асистент не використовує зовнішній LLM API. Це зроблено навмисно: фокус домашнього завдання — не якість генерації великої моделі, а побудова eval pipeline і guardrails навколо AI-асистента.

## Що перевірялося

Eval pipeline перевіряє чотири класи ризиків:

1. PII leakage.
2. Prompt injection.
3. Hallucinations / faithfulness.
4. Refusal patterns.

Golden dataset містить 15 кейсів. Для кожного кейсу задані:

- очікувана поведінка;
- фрази, які відповідь повинна містити;
- фрази, яких у відповіді не повинно бути;
- reference policy.

## Результати

| Category | Passed | Total | Pass rate |
|----------|--------|-------|-----------|
| faithfulness | 4 | 4 | 100.0% |
| hallucination | 2 | 2 | 100.0% |
| pii_leakage | 3 | 3 | 100.0% |
| prompt_injection | 3 | 3 | 100.0% |
| refusal_patterns | 3 | 3 | 100.0% |
| **overall** | **15** | **15** | **100.0%** |

Повні результати збережені у:

```text
results/eval_results.json
results/eval_results.csv
```

## Що було знайдено під час роботи

Перший прогін eval pipeline не був ідеальним: assistant проходив лише 10 з 15 кейсів. Проблеми були типові для guardrails:

- password reset помилково сприймався як PII leakage;
- refusal text сам містив заборонені слова типу `API keys`, через що тест ловив потенційний leakage;
- prompt injection з ownership transfer не маркувався як refusal;
- hallucination answers були безпечні, але формулювання не збігалося з expected phrase у golden dataset.

Після калібрування guardrails фінальний прогін дав 15/15.

## Production readiness verdict

Verdict: **ship to limited beta, not full production yet**.

Причина: на поточному golden dataset assistant проходить 100% safety/eval кейсів, але dataset має лише 15 прикладів. Для production цього мало. Такий результат достатній, щоб показати, що guardrails design працює на базових сценаріях, але недостатній, щоб гарантувати стабільність на реальному трафіку.

## Чому не full ship

Поточний pipeline має обмеження:

- dataset маленький;
- assistant deterministic, не справжній LLM;
- немає adversarial paraphrase набору;
- немає multilingual injection cases;
- немає автоматичного LLM-as-judge;
- немає production monitoring після deploy.

Перед production треба розширити golden dataset хоча б до 100-200 кейсів, додати реальні support logs після redaction, додати paraphrase attacks і прогнати eval на справжній LLM-based асистент.

## Бізнес-висновок

Для internal beta assistant можна запускати з поточними guardrails, якщо відповіді логуються і є human escalation. Для public customer-facing production я б ще не запускав. Спочатку треба збільшити eval coverage, протестувати реальну LLM-модель і додати continuous monitoring для PII leakage, prompt injection і hallucination incidents.
