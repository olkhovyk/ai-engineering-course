# Заняття 6: LLM Engineering (API + Self-hosted)

## 🎯 Мета

Розібратись у різниці між **API-first** (OpenAI, Claude, Gemini) та **self-hosted** LLM архітектурами (Ollama, llama.cpp, vLLM). Побудувати практичний агент для екстракції структурованої інформації з неструктурованого тексту та порівняти якість / вартість / швидкість на реальних даних.

---

## 📚 Матеріали

### Визуалізації
- **[llm-vs-slm.html](llm-vs-slm.html)** — інтерактивне порівняння Large Language Models vs Small Language Models (таблиця, use cases, decision flow)
- **[quantization-demo.html](quantization-demo.html)** — як квантизація зменшує розмір моделі (FP32 → INT4) з інтерактивними слайдерами та live-демонстрацією

---

## 🏠 Архітектура

```
lesson-06-llm-engineering/
├── README.md                    (цей файл)
├── llm-vs-slm.html             (порівняння архітектур)
├── quantization-demo.html       (демонстрація квантизації)
├── homework/
│   ├── extraction_agent.py      (стартовий код)
│   ├── eval_matrix.xlsx         (шаблон для результатів)
│   └── HOMEWORK.md              (детальне завдання)
└── samples/
    ├── simple_meeting.txt       (простий протокол)
    ├── chaotic_standup.txt      (хаотична дискусія)
    └── technical_sync.txt       (технічна зустріч)
```

---

## 🧠 Концепція

### Два світи LLM

| Аспект | API (CloudFirst) | Self-Hosted (Local) |
|--------|------------------|-------------------|
| **Куди йдуть дані** | OpenAI / Anthropic сервери | Твій сервер / ноутбук |
| **Контроль** | Нульовий | Повний |
| **Вартість** | $0.001 – $0.06 за 1K токенів | $0 (після купівлі GPU) |
| **Latency** | 1–10 сек (інтернет) | 50–500 мс (локально) |
| **Якість** | ⭐⭐⭐⭐⭐ (Claude 3.5 Sonnet, GPT-4o) | ⭐⭐⭐⭐☆ (Llama 3.1 70B) |
| **Privacy** | ❌ Дані в хмарі | ✅ Все локально |
| **Де це работает** | Production API сервісів | Healthcare, Banking, Defense |

### Task: Extraction Agent

Агент має отримати текст транскрипту робочої зустрічі (неструктурований, зі словами-паразитами, перерванням), і повернути **JSON** з трьома полями:

```json
{
  "summary": "На зустрічі обговорили план розробки нового dashboard та розподілили завдання.",
  "tasks": [
    {
      "owner": "Анна",
      "task": "Реалізувати API для користувачів",
      "deadline": "2025-05-15"
    },
    {
      "owner": "Іван",
      "task": "Дизайн UI prototype",
      "deadline": "2025-05-10"
    }
  ],
  "decisions": [
    "Використовувати React для frontend",
    "Встановити дедлайн на 15 травня",
    "Код review обов'язковий перед merge"
  ]
}
```

---

## 🏠 Домашнє завдання

### Завдання 1: Setup

```bash
# Встановити Ollama (https://ollama.ai)
ollama pull llama2  # або mistral, neural-chat

# Запустити локально
ollama serve

# Встановити Python бібліотеки
pip install openai requests python-dotenv
```

### Завдання 2: Реалізувати Extraction Agent

Файл: `homework/extraction_agent.py`

**Код стартус:**

```python
import openai
import requests
import json
import sys

# ── OLLAMA (self-hosted) ──
def call_ollama(prompt: str) -> str:
    """Викликає локальну модель через Ollama API"""
    response = requests.post(
        'http://localhost:11434/api/generate',
        json={
            "model": "llama2",  # або mistral
            "prompt": prompt,
            "stream": False
        }
    )
    return response.json()['response']

# ── OPENAI (cloud) ──
def call_openai(prompt: str) -> str:
    """Викликає GPT-4o-mini через OpenAI API"""
    client = openai.OpenAI(api_key="YOUR_API_KEY")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """You are a meeting transcription parser. 
Extract tasks, decisions, and a summary from meeting text.
Return ONLY valid JSON, no markdown, no extra text."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

# ── EXTRACTION LOGIC ──
def extract_meeting_data(text: str, provider: str = "ollama") -> dict:
    """
    Витягує структурований JSON з неструктурованого тексту зустрічі.
    
    Args:
        text: Транскрипт / протокол зустрічі
        provider: "ollama" або "openai"
    
    Returns:
        dict: {"summary": str, "tasks": [...], "decisions": [...]}
    """
    
    prompt = f"""Прочитай цей текст зустрічі та витягни:
1. summary (одна речення на українській)
2. tasks (список завдань з owner, task, deadline)
3. decisions (рішення, які було прийнято)

Текст:
{text}

Поверни ТІЛЬКИ JSON, нічого більше:
{{
  "summary": "...",
  "tasks": [
    {{"owner": "...", "task": "...", "deadline": "..."}}
  ],
  "decisions": ["..."]
}}"""
    
    if provider == "ollama":
        response_text = call_ollama(prompt)
    elif provider == "openai":
        response_text = call_openai(prompt)
    else:
        raise ValueError(f"Unknown provider: {provider}")
    
    # Спробуй спарсити JSON
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON: {response_text[:200]}")
        return None

# ── MAIN ──
if __name__ == "__main__":
    # Читай з файлу або stdin
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        with open(input_file, 'r', encoding='utf-8') as f:
            meeting_text = f.read()
    else:
        meeting_text = """
        Анна: Добрий день. Новий квартал, новий дизайн. 
        У нас є потрібно зробити новий dashboard для аналітики.
        Іван, ти можеш взяти дизайн UI? Дедлайн п'ятниця, ні, краще наступна п'ятниця.
        Анна: Мартин, ты на backend? Давай API для користувачів.
        Мартин: Окей, я можу, але мені потрібні spec. До 15 травня, так?
        Анна: Все так. І хлопці, kod review обов'язковий перед merge, це точно вирішено.
        """
    
    # Тестуй обидві моделі
    print("🤖 Testing Ollama (local)...")
    result_local = extract_meeting_data(meeting_text, provider="ollama")
    print(json.dumps(result_local, indent=2, ensure_ascii=False))
    
    print("\n☁️  Testing OpenAI (cloud)...")
    result_cloud = extract_meeting_data(meeting_text, provider="openai")
    print(json.dumps(result_cloud, indent=2, ensure_ascii=False))
```

**Що потрібно зробити:**

1. Заповни `YOUR_API_KEY` реальним OpenAI ключем
2. Переконайся, що `ollama serve` запущена на `localhost:11434`
3. Запусти на всіх 3 наборах даних (простий, хаотичний, складний)
4. Запиши результати до таблиці оцінювання

### Завдання 3: Evaluation Matrix

Файл: `homework/eval_results.csv` або `eval_results.xlsx`

Збери результати для кожного датасету (simple, chaotic, technical) для обидвох провайдерів (Ollama, OpenAI) в таблицю:

#### Метрики для вимірювання:

| Метрика | Як вимірювати | Приклад |
|---------|---------------|---------|
| **JSON валідність** | Чи вдається `json.loads()` спарсити відповідь? | ✅ успішно / ❌ SyntaxError |
| **Знайдено завдань** | Скільки елементів у масиві `tasks`? | 3/3 знайдено (або 2/4 — мало) |
| **Галюцинації** | Чи вигадала модель людей/дати, яких нема в тексті? | +0 ✅ / +2 ❌ (вигадані люди) |
| **Токени (input)** | Довжина промпта (приблизно слово = 1.3 токена) | ~245 токенів |
| **Токени (output)** | Довжина JSON відповіді | ~120 токенів |
| **Токени (total)** | input + output | ~365 токенів |
| **Вартість ($)** | Для OpenAI: `tokens × $0.0003` / Для Ollama: $0 | $0.00011 або $0 |
| **Latency (сек)** | Виміряй `time.time()` до/після запиту | 1.2 сек (Ollama) / 0.3 сек (OpenAI) |

#### Структура таблиці результатів:

```
Dataset     | Provider | JSON ✓ | Tasks | Halluc | Tokens | Cost  | Latency
------------|----------|--------|-------|--------|--------|-------|--------
simple      | Ollama   | ✅     | 3/3  | 0      | 245    | $0    | 1.2s
simple      | OpenAI   | ✅     | 3/3  | 0      | 267    | $0.00008 | 0.3s
chaotic     | Ollama   | ❌     | 2/4  | +2     | 289    | $0    | 0.9s
chaotic     | OpenAI   | ✅     | 4/4  | 0      | 312    | $0.00009 | 0.4s
technical   | Ollama   | ✅     | 1/5  | +1     | 334    | $0    | 1.8s
technical   | OpenAI   | ✅     | 5/5  | 0      | 356    | $0.00011 | 0.5s
```

#### Як розраховувати метрики:

**JSON Валідність:**
```
спробуй спарсити результат json.loads(response)
якщо вийде → ✅
якщо SyntaxError → ❌
```

**Знайдено завдань:**
```
відеолічи реальні завдання в тексті (вручну)
порівняй скільки модель витягнула
приклад: текст має 5 завдань, модель знайшла 3 → 3/5
```

**Галюцинації:**
```
для кожного завдання перевір чи ім'я/дата існує в оригіналі
ім'я "Мартин" є в тексті? Так → OK
дата "15 травня" згадується? Ні → +1 галюцинація
```

**Токени:**
```
вхідний текст: розділи на пробіли, помнож на 1.3
вихідний JSON: розділи на пробіли, помнож на 1.3
всього: input + output
(або використовуй OpenAI API для точного лічення)
```

**Вартість:**
```
Ollama → завжди $0 (self-hosted)
OpenAI → (total_tokens / 1_000_000) × $0.0003
приклад: 267 токенів = $0.00008
```

**Latency:**
```
import time
start = time.time()
result = agent(text, provider="openai")
latency = time.time() - start
print(f"{latency:.2f} сек")
```

### Завдання 4: Скріншоти доказів виконання

Здай разом з кодом наступні скріншоти:

| # | Файл | Що показує | Чому важливо |
|---|------|-----------|------------|
| 1 | **setup.png** | Вивід `ollama serve` в терміналі | Доказ що Ollama запущена локально |
| 2 | **simple_result_ollama.png** | JSON вивід від Ollama для простого текста | Робить чи не робить валідний JSON |
| 3 | **simple_result_openai.png** | JSON вивід від OpenAI для простого текста | Порівняння якості на простому |
| 4 | **chaotic_result_ollama.png** | JSON вивід від Ollama для хаотичного текста | Видно слабину локальної моделі |
| 5 | **chaotic_result_openai.png** | JSON вивід від OpenAI для хаотичного текста | Показує що API стійкіша |
| 6 | **eval_table.png** | Таблиця результатів (CSV або Excel) | Всі 6 метрик в одній таблиці |

**Де розміщувати скріншоти:**
```
homework/
├── screenshots/
│   ├── setup.png
│   ├── simple_result_ollama.png
│   ├── simple_result_openai.png
│   ├── chaotic_result_ollama.png
│   ├── chaotic_result_openai.png
│   └── eval_table.png
├── extraction_agent.py
├── eval_results.csv
└── ANALYSIS.md
```

**Як робити скріншоти:**

Простий текст:
```bash
python extraction_agent.py samples/simple_meeting.txt
# Скопіюй вивід → роби скріншот → зберіги як simple_result_ollama.png
```

Хаотичний текст:
```bash
python extraction_agent.py samples/chaotic_standup.txt
# Скріншот → chaotic_result_ollama.png
```

Setup:
```bash
ollama serve
# Скріншот коли вивід показує "listening on..." → setup.png
```

### Завдання 4: Аналіз та висновки

Напиши документ `homework/ANALYSIS.md` з відповідями:

1. **Коли використовувати Ollama?** (self-hosted)
   - На які критерії дивитися при виборі?
   - Яка мінімальна якість для твоєї задачі?

2. **Коли використовувати OpenAI?**
   - Які уроки ти отримав?

3. **Гібридний підхід**
   - Чи можна використовувати обидві моделі одночасно (ensemble)?
   - Наприклад: спробувати Ollama (швидко, дешево), якщо JSON невалідний → fallback на OpenAI

4. **Розширення завдання**
   - Як модифікувати агента для支持 інших мов (українська → англійська → українська)?
   - Як добавити `confidence_score` для кожного завдання?

---

## 📊 Очікувані результати

### Для простого набору даних:
- Ollama (Llama 2 7B): ~85% точность, 1.2s, $0
- OpenAI (GPT-4o-mini): ~99% точність, 0.3s, $0.0001

### Для хаотичного набору:
- Ollama: Часто робить помилки (галюцинує імена, пропускає завдання)
- OpenAI: Стійка до шуму, але інколи переінтерпретує

### Висновки:
- **Для критичних task** → використовуй Cloud API
- **Для масового обробку з жорсткими дедлайнами** → Self-hosted
- **Для баланс якість/вартість** → Гібридний підхід

---

## 🛠️ Інструменти

| Інструмент | Версія | Для чого |
|-----------|--------|----------|
| Ollama | 0.1.31+ | Local LLM inference |
| llama2 або mistral | Latest | SLM для self-hosted |
| OpenAI API | GPT-4o-mini | Cloud baseline |
| Python requests | 2.28+ | HTTP запити до Ollama |
| python-dotenv | 0.19+ | Безпечне зберігання API ключа |
| json | Built-in | Парсинг результатів |

---

## 📝 Дедлайн

**Здачі до:** 2025-06-15

**Структура здачи:**
```
homework/
├── extraction_agent.py       (код)
├── eval_matrix.xlsx          (таблиця оцінки)
├── ANALYSIS.md               (висновки)
├── samples/
│   ├── simple_meeting.txt
│   ├── chaotic_standup.txt
│   └── technical_sync.txt
└── results/
    ├── simple_ollama.json
    ├── simple_openai.json
    ├── chaotic_ollama.json
    ├── chaotic_openai.json
    ├── technical_ollama.json
    └── technical_openai.json
```

---

## 🎓 Что ви найдете з цього

✅ Розумієте різницю між API та self-hosted архітектурами  
✅ Знаєте, як обирати модель для свого usecase  
✅ Вміють писати промпти для structured output (JSON)  
✅ Розуміють trade-off: якість ↔ вартість ↔ приватність  
✅ Можете deployit локальний LLM за 5 хвилин (Ollama)  

---

## 📚 Посилання

- **Ollama:** https://ollama.ai
- **Llama 2:** https://llama.meta.com
- **OpenAI API:** https://platform.openai.com/docs
- **Anthropic Claude API:** https://console.anthropic.com
- **LiteLLM (uni SDK):** https://github.com/BerriAI/litellm
- **GGUF (quantization):** https://github.com/ggerganov/llama.cpp

---

**Автор:** AI Engineering Course  
**Мова:** Українська  
**Рівень:** Intermediate (потрібні знання Python + базова Python API)
