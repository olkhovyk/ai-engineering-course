# Lesson 11 Report

## Що було зроблено

Я реалізував personal finance assistant у двох архітектурах: простий `baseline` і multi-agent `crew` на LangGraph. Обидві архітектури використовують однакові deterministic tools для роботи з транзакціями: підрахунок витрат по категорії, топ категорій, subscriptions, delivery after 21:00, cashflow, savings opportunities і fraud/escalation сценарії. Це важливо, бо фінансові числа рахуються кодом, а не LLM.

У `crew` workflow побудований через LangGraph `StateGraph`: `route -> stats_agent / savings_agent / risk_agent -> compose`. Для observability підключений LangSmith tracing, тому у waterfall видно LangGraph nodes, router, composer і OpenRouter виклики. Для тестування зроблений Streamlit UI з вкладками `Chat` і `Eval`. Golden set також можна прогнати через LangSmith Datasets/Experiments за допомогою `scripts/langsmith_eval.py`. Для ambiguous follow-up запитів додано `ConversationContext`, який пам'ятає попередню тему діалогу.

## Eval results

Golden set містить 16 кейсів. Я прогнав його у двох режимах.

### Rule router + template composer

| architecture | cases | intent accuracy | tool accuracy | avg latency ms |
| --- | ---: | ---: | ---: | ---: |
| baseline | 16 | 1.00 | 1.00 | 1.822 |
| crew | 16 | 1.00 | 1.00 | 12.708 |

У цьому режимі обидві архітектури дали ідеальну якість, бо routing і formatting deterministic. Baseline значно швидший, бо не має LangGraph orchestration overhead. Crew повільніший, але дає кращу структуру і traceability.

### LLM router + LLM composer

| architecture | cases | intent accuracy | tool accuracy | avg latency ms |
| --- | ---: | ---: | ---: | ---: |
| baseline | 16 | 0.75 | 0.75 | 5285.764 |
| crew | 16 | 0.81 | 0.81 | 4415.725 |

У LLM режимі точність нижча, бо модель іноді неправильно класифікує intent або tool. Crew показав трохи кращу якість і нижчу середню latency, але це не означає, що LangGraph автоматично робить систему розумнішою. Основна користь LangGraph тут у тому, що workflow стає явним і його легше дебажити в LangSmith.

## Висновки

Для простих запитів і маленького структурованого dataset baseline є найефективнішим варіантом: він простий, швидкий і в rule/template режимі має 100% accuracy на golden set. LangGraph crew має overhead, але виграє в архітектурі: можна додавати окремі agent nodes, дивитися waterfall у LangSmith і не перетворювати код на один великий dispatcher.

Multi-turn підтримка покриває простий ambiguous сценарій: після запиту "Скільки витратив на каву?" користувач може написати "А за місяць?", і система збереже попередню категорію `coffee`, але змінить period на `current_month`. Це не повна довгострокова пам'ять, але достатній приклад session context для домашнього завдання.

LLM router варто використовувати для більш природних, нечітких або помилкових запитів, але його треба додатково покращувати: кращий prompt, краща модель, examples у prompt або fallback на rule-based validation. У production я б залишив deterministic tools для всіх фінансових обчислень, а LLM використовував тільки для routing і natural-language відповіді. Для масштабування crew-архітектури я б залишив LangGraph, використовував LangSmith Experiments як managed eval і розширив golden set більш складними multi-step сценаріями.

## Що використано зі стеку

Використано Python, LangGraph, OpenRouter, LangSmith tracing, LangSmith Datasets/Experiments, Streamlit UI і локальний golden set eval. Не використовувались FastAPI, Pydantic, SQLite/Postgres і vector store, бо в цій задачі дані маленькі, структуровані і повністю поміщаються в пам'ять.
