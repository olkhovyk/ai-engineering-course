# Lesson 13 Homework: Containers for AI

## What is inside

This submission containerizes the provided FastAPI RAG boilerplate.

Files:

- `Dockerfile.naive` - baseline image with simple `COPY . .` and `pip install`.
- `Dockerfile` - optimized multi-stage image with `python:3.11-slim`, non-root user and `HEALTHCHECK`.
- `.dockerignore` - excludes local files and caches from Docker build context.
- `docker-compose.yml` - starts the RAG API with Redis, Qdrant and Langfuse.

## Environment

Create `.env` from `.env.example` and add an OpenAI API key:

```env
OPENAI_API_KEY=your-key-here
EMBEDDER_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o-mini
```

Do not commit or submit the real `.env` file.

## Build commands

Naive image:

```powershell
Measure-Command { docker build -f Dockerfile.naive -t lesson13-rag-api:naive . }
```

Optimized multi-stage image:

```powershell
Measure-Command { docker build -f Dockerfile -t lesson13-rag-api:multi-stage . }
```

Rebuild after a code change:

```powershell
Measure-Command { docker build -f Dockerfile.naive -t lesson13-rag-api:naive . }
Measure-Command { docker build -f Dockerfile -t lesson13-rag-api:multi-stage . }
```

Image sizes:

```powershell
docker images lesson13-rag-api
```

## Run with Docker Compose

```powershell
docker compose up -d --build
```

Check services:

```powershell
docker compose ps
```

Check health:

```powershell
curl http://localhost:8000/health
```

Ask endpoint:

```powershell
curl -X POST http://localhost:8000/ask `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"What is a vector database?\"}"
```

Stop services:

```powershell
docker compose down
```

## Cold start measurement

One simple manual way:

```powershell
docker compose down
$started = Get-Date
docker compose up -d --build
while ($true) {
  try {
    $body = Invoke-RestMethod http://localhost:8000/health
    if ($body.status -eq "ok") { break }
  } catch {}
  Start-Sleep -Seconds 1
}
((Get-Date) - $started).TotalSeconds
```

## Metrics

Fill this table after building and running both images locally.

| Metric | Naive | Multi-stage |
|---|---:|---:|
| Image size | 1.76GB | 367MB |
| Build time | 45.5s | 30.9s |
| Rebuild after code change | 19.0s | 2.0s |
| Cold start до `/health=ok` | 1.54s | 2.54s |

Cold start was measured with `docker run` for both images, without the extra startup overhead of Redis, Qdrant, Langfuse and Postgres from Docker Compose.

## Screenshots to submit

Required screenshots:

- `docker images lesson13-rag-api` showing both images.
- `curl -X POST localhost:8000/ask` with a successful answer.
- `docker compose ps` showing the API, Redis, Qdrant, Langfuse and Postgres services.

## Notes

The boilerplate app keeps embeddings in memory and calls OpenAI directly for embeddings and chat completions. Qdrant, Redis and Langfuse are included in `docker-compose.yml` as production-like infrastructure dependencies for the homework container stack.
