# Lesson 10 RAG API Solution

Це мінімальний production-style RAG API для Q&A по документу `data/source.md`.
Сервіс індексує документ у Qdrant, шукає релевантні chunks, передає їх у OpenRouter LLM і стрімить відповідь через SSE.

## Stack

- FastAPI + Uvicorn
- OpenRouter для LLM
- `sentence-transformers/all-MiniLM-L6-v2` для embeddings
- Qdrant для chunks і semantic cache
- Redis для token-based rate limit
- SQLite для usage/cost tracking
- Arize Phoenix для локального tracing/observability
- Простий HTML UI на `/`

## Run Locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

У `.env` треба додати:

```env
OPENROUTER_API_KEY=sk-or-v1-...
```

Підняти залежності:

```powershell
docker compose up -d
```

Проіндексувати документ:

```powershell
python scripts/index.py
```

Запустити API:

```powershell
uvicorn app.main:app --reload --port 8000
```

UI:

```text
http://127.0.0.1:8000/
```

Phoenix UI:

```text
http://localhost:6006
```

## Test API Keys

```text
demo-free-key       звичайний free tier
demo-pro-key        pro tier
demo-enterprise-key enterprise tier
demo-low-key        спеціальний ключ для rate limit тесту
```

## Useful Checks

Health:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Clear semantic cache:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/cache/clear" `
  -H "X-API-Key: demo-free-key"
```

Streaming request:

```powershell
curl.exe -N -X POST "http://127.0.0.1:8000/chat/stream" `
  -H "Content-Type: application/json" `
  -H "X-API-Key: demo-free-key" `
  -d "{\"message\":\"Where should application config be stored?\"}"
```

Usage:

```powershell
curl.exe "http://127.0.0.1:8000/usage/today" `
  -H "X-API-Key: demo-free-key"
```

Breakdown:

```powershell
curl.exe "http://127.0.0.1:8000/usage/breakdown" `
  -H "X-API-Key: demo-free-key"
```

## Test Questions

Для перевірки RAG retrieval можна використовувати такі питання:

```text
Where should application config be stored?
```

```text
What does the document say about backing services?
```

```text
How should a twelve-factor app handle logs?
```

```text
Why should processes be stateless?
```

```text
What is the difference between build, release, and run?
```

## Phoenix Tracing

Tracing optional. Якщо не треба Phoenix, залишити:

```env
PHOENIX_ENABLED=false
```

Якщо треба локальний tracing, у `.env`:

```env
PHOENIX_ENABLED=true
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces
PHOENIX_PROJECT_NAME=lesson-10-rag-api
```

Підняти Phoenix разом з іншими сервісами:

```powershell
docker compose up -d
```

Після `/chat/stream` у Phoenix мають з'явитися spans:

```text
chat-stream
auth
rate-limit
embed-query
cache-check
vector-search
llm-call
cache-store
usage-log
```

Для швидкої перевірки tracing без LLM:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/debug/trace-test" `
  -H "X-API-Key: demo-free-key"
```

## Fallback Test

У `.env`:

```env
FORCE_BAD_PRIMARY=true
```

Після перезапуску сервера перша модель у chain стає невалідною:

```text
openai/this-does-not-exist
```

Після запиту в `done` event має бути:

```json
"fallback_used": true
```

Після тесту повернути:

```env
FORCE_BAD_PRIMARY=false
```

## Rate Limit Test

У UI або curl використати ключ:

```text
demo-low-key
```

Цей ключ має `50 tokens/min`, тому `/chat/stream` швидко повертає:

```text
429 Rate limit exceeded
```
