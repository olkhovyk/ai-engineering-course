# Lesson 11 Solution Notes

## Що реалізовано

Я зробив personal finance assistant з двома архітектурами:

- `baseline` - простий single-agent pipeline без agent framework.
- `crew` - multi-agent orchestration через LangGraph.

Обидві архітектури працюють з одним і тим самим набором deterministic tools з `src/tools.py`, тому фінансові числа рахуються кодом, а не вигадуються LLM.

## Архітектура

### Baseline

Baseline pipeline:

```text
question
  -> router
  -> tool call
  -> composer
  -> answer
```

Baseline знаходиться у `src/baseline_agent.py`.

### LangGraph Crew

Crew pipeline реалізований у `src/langgraph_crew.py` через `StateGraph`:

```text
START
  -> route
  -> stats_agent / savings_agent / risk_agent
  -> compose
  -> END
```

Агенти:

- `stats_agent` - витрати по категорії, топ категорій, delivery, cashflow, subscriptions.
- `savings_agent` - можливості для економії.
- `risk_agent` - fraud / out-of-scope сценарії.

LangGraph потрібен тут не для магії, а для явної orchestration-схеми: видно nodes, conditional routing і фінальний compose step.

## Де використовується LLM

LLM використовується тільки у двох місцях:

- `router=llm` - модель визначає `intent` і `category`.
- `composer=llm` - модель формує людську відповідь на основі вже порахованих facts.

Фінансові обчислення не робляться моделлю. Вони робляться deterministic tools.

OpenRouter client знаходиться у `src/llm_router.py`.

## LangSmith

LangSmith tracing підключений через `src/langsmith_tracing.py`.

Щоб увімкнути traces, треба додати в `.env`:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=lesson-11-finance-crew
```

У LangSmith видно workflow приблизно такого виду:

```text
langgraph.crew
  langgraph.route
  router.llm або router.rule
  langgraph.savings_agent / langgraph.stats_agent / langgraph.risk_agent
  langgraph.compose
  composer.llm або composer.template
```

Це дає можливість дивитися latency, inputs/outputs і waterfall виконання.

## UI

UI зроблений на Streamlit у `app.py`.

Запуск:

```powershell
streamlit run app.py
```

У sidebar можна вибрати:

- `Architecture`: `baseline` або `crew`
- `Router`: `rule` або `llm`
- `Composer`: `template` або `llm`

Є дві вкладки:

- `Chat` - ручне тестування одного запиту.
- `Eval` - запуск golden set для baseline і crew.

## Eval

Golden set лежить у `eval/golden_set.json`.

Локальний eval runner:

```powershell
python src\eval_runner.py --router rule --composer template
python src\eval_runner.py --router llm --composer llm
```

Через UI те саме можна запускати у вкладці `Eval`.

Метрики:

- intent accuracy
- tool accuracy
- average latency

Результати пишуться у `results/eval_results.csv`.

## LangSmith Experiments

Окремо є managed eval через LangSmith Datasets/Experiments:

```powershell
python scripts\langsmith_eval.py --router rule --composer template
python scripts\langsmith_eval.py --router llm --composer llm
```

Скрипт `scripts/langsmith_eval.py`:

- створює dataset `lesson-11-finance-golden-set`;
- завантажує 16 прикладів з `eval/golden_set.json`;
- запускає experiments для `baseline` і `crew`;
- рахує custom evaluators `intent_accuracy` і `tool_accuracy`;
- зберігає результати у LangSmith для side-by-side порівняння.

## Multi-turn / ambiguous follow-up

Для простого multi-turn сценарію додано `ConversationContext` у `src/conversation.py`.

Приклад:

```text
User: Скільки витратив на каву?
Assistant: coffee: $... за останні 7 днів

User: А за місяць?
Assistant: coffee: $... за current_month
```

Другий запит сам по собі ambiguous, бо в ньому немає категорії. `ContextualRouter` спочатку перевіряє conversation context і бачить, що попередня тема була `category_spending + coffee`. Тому він перетворює follow-up на:

```text
intent=category_spending
category=coffee
period=current_month
```

У Streamlit UI context зберігається в `st.session_state`. Для очищення є кнопка `Clear conversation` у sidebar.

## Як запустити проект

1. Встановити залежності:

```powershell
pip install -r requirements.txt
```

2. Створити `.env` на основі `.env.example`.

Для LLM:

```env
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_ROUTER_MODEL=mistralai/mistral-nemo
OPENROUTER_COMPOSER_MODEL=mistralai/mistral-nemo
```

Для LangSmith:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=lesson-11-finance-crew
```

3. Запустити UI:

```powershell
streamlit run app.py
```

## Що зі стеку використано

Використано:

- Python
- LangGraph
- OpenRouter
- LangSmith tracing
- LangSmith Datasets/Experiments
- Streamlit
- local golden set eval

Не використано:

- FastAPI
- Pydantic
- SQLite/Postgres
- vector store

Причина: для цієї задачі дані маленькі й структуровані, тому CSV + deterministic tools достатньо. Основний фокус домашки - agent orchestration, tracing, eval і порівняння baseline vs crew.

## Висновок

Baseline простіший і швидший для простих запитів. LangGraph crew має більше сенсу, коли сценарій розростається: різні типи задач, різні спеціалізовані агенти, observability, окремі nodes у trace і можливість розширювати workflow без великого `if/else` в одному файлі.

Multi-turn context поки зроблений мінімально: він підтримує follow-up типу "А за місяць?" для попереднього category-spending запиту. Для production це треба було б розширити до повноцінної session memory з явним збереженням topic, period, account і уточненнями від користувача.
