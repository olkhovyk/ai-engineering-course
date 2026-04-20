# 🦙 Local Llama Demo

Інтерактивне демо для пояснення як використовувати локальну LLM модель через Ollama.

## Структура

```
local-llama-demo/
├── index.html       # Інтерфейс демо
├── app.py          # FastAPI сервер (обгортка для Ollama)
├── requirements.txt # Залежності
└── README.md       # Цей файл
```

## Підготовка

### 1. Встановити Ollama
- Завантажити з [ollama.ai](https://ollama.ai)
- Встановити для вашої OS (macOS, Linux, Windows WSL)

### 2. Завантажити модель
```bash
ollama pull llama2
# або Mistral (менше памяті, краща якість)
ollama pull mistral
```

### 3. Запустити Ollama сервер
```bash
ollama serve
# Сервер буде на localhost:11434
```

## Запуск демо

### Варіант 1: Просто з браузера (статичний)
```bash
# Відкрити index.html в браузері
# НЕ буде працювати через CORS!
```

### Варіант 2: З FastAPI обгорткою (рекомендовано)

1. Встановити залежності:
```bash
pip install -r requirements.txt
```

2. Запустити FastAPI сервер (в окремому терміналі):
```bash
python app.py
# або
uvicorn app:app --reload --port 8000
```

3. Відкрити браузер на `http://localhost:8000`

## Як це працює

```
Браузер → FastAPI (localhost:8000) → Ollama (localhost:11434)
```

FastAPI перехоплює запити з браузера і перенаправляє їх до Ollama, обходячи CORS обмеження.

## API Endpoints

### GET /api/tags
Отримати список доступних моделей
```bash
curl http://localhost:8000/api/tags
```

### POST /api/generate
Отправити запит до моделі
```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "prompt": "Hello",
    "stream": false
  }'
```

## Продуктивність

На вашій машині середня:
- **Llama2 7B**: 2-5 сек per 100 tokens
- **Mistral 7B**: 2-4 сек per 100 tokens

Залежить від:
- CPU потужності
- Кількості памяті
- Довжини промпту і відповіді
