# REPORT

Зроблено мінімальний RAG API для Q&A по документу `data/source.md`.
Документ розбивається на Markdown-aware chunks: кожна секція `##` стає окремим chunk, тому retrieval повертає більш точні sources.
Embeddings рахуються локально через `sentence-transformers/all-MiniLM-L6-v2`, а chunks зберігаються в Qdrant collection `rag_chunks`.
Endpoint `/chat/stream` приймає `{message}` і повертає SSE events з токенами та фінальним `done` event.
У `done` event є `sources`, `usage`, `cost_usd`, `cache_hit`, `fallback_used`, `model`, `latency_ms` і `ttft_ms`.


Для `demo-free` tier було використано `openrouter/free`, free fallback модель і дешеву платну `mistralai/mistral-nemo`.
Semantic cache зроблений у Qdrant в окремій collection `rag_cache`; повторний однаковий запит дає `cache_hit=true` і `cache_similarity≈1.0`.
Rate limiting зроблений через Redis token bucket per API key.
Для демонстрації rate limit доданий ключ `demo-low-key` з маленьким лімітом `50 tokens/min`, який повертає `429`.

Usage і cost tracking зберігаються в SQLite `data/usage.db`.
Після fallback-тесту з `mistralai/mistral-nemo` cost tracking показав ненульову мікровартість запиту.
Auth працює через header `X-API-Key`; без ключа API повертає `401`.
Prompt injection defense перевіряє input patterns, наприклад `Ignore previous instructions`, і повертає `400 Suspicious input detected`. і логується у suspicious_requests.log
Для fallback-тесту додано env flag `FORCE_BAD_PRIMARY=true`, який підставляє невалідну primary model і змушує сервіс перейти на fallback.
Також зробив простий UI на `/`, щоб тестувати streaming, cache, usage, fallback і rate limit без Postman.
Для observability додано локальний Arize Phoenix через Docker Compose і OpenTelemetry spans.
Tracing вмикається через `PHOENIX_ENABLED=true`, після чого у Phoenix видно pipeline spans: `auth`, `rate-limit`, `embed-query`, `cache-check`, `vector-search`, `llm-call`, `cache-store`, `usage-log`.
У trace можна побачити user query, retrieved sources, prompt для LLM і фінальну відповідь.

Що не доведено до повного production рівня: публічний deploy на Fly.io.
Локально основні API layer patterns працюють: streaming, RAG retrieval, sources, semantic cache, auth, rate limit, cost tracking, fallback, tracing і базова prompt-injection defense.
