"""
Demo: Локальні embeddings для RAG — найпоширеніший сценарій PyTorch для AI-інженера.

Сценарій:
  Будуємо пошук по внутрішній документації.
  Чому не OpenAI API? Конфіденційність / вартість / контроль.
  Беремо sentence-transformers → під капотом PyTorch.

  Показуємо 4 рівні роботи:
    1. Високий рівень: SentenceTransformer — одна строчка
    2. Середній рівень: HuggingFace AutoModel — контроль над пулінгом
    3. Низький рівень: PyTorch tensors — повний контроль
    4. Production: батчінг, latency, порівняння з API

Requires: pip install sentence-transformers torch
"""
import time
import torch
import torch.nn.functional as F

device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")


def sync():
    if device == "cuda": torch.cuda.synchronize()
    elif device == "mps": torch.mps.synchronize()


# ==============================================================
# Тестові дані — внутрішня документація компанії
# ==============================================================
documents = [
    "Для скидання пароля перейдіть у Налаштування → Безпека → Змінити пароль",
    "Оплата підписки відбувається автоматично першого числа кожного місяця",
    "Для підключення API потрібно згенерувати ключ у розділі Інтеграції",
    "Якщо додаток не запускається, спробуйте очистити кеш у налаштуваннях",
    "Корпоративний тариф включає необмежену кількість користувачів",
    "Двофакторна автентифікація вмикається через Google Authenticator",
    "Резервне копіювання даних відбувається щоночі о 03:00",
    "Для експорту даних оберіть Звіти → Експорт → CSV або JSON",
    "Підтримка працює з 9:00 до 18:00 за київським часом",
    "Видалення акаунту можливе через запит у службу підтримки",
]
query = "як змінити пароль"

print("=" * 65)
print("ЛОКАЛЬНІ EMBEDDINGS ДЛЯ RAG")
print("=" * 65)
print(f"""
  Задача: пошук по {len(documents)} документах внутрішньої бази знань.
  Запит: "{query}"

  Чому локально, а не OpenAI API?
    • Конфіденційність — дані не покидають сервер
    • Вартість — $0 замість $0.0001/1K токенів × мільйони документів
    • Контроль — можна файнтюнити під свій домен
    • Latency — немає мережевих затримок

  device: {device}
""")


# ==============================================================
# РІВЕНЬ 1: SentenceTransformer — одна строчка (показуємо код)
# ==============================================================
print("=" * 65)
print("РІВЕНЬ 1: SentenceTransformer (високий рівень)")
print("=" * 65)
print("""
  Найпростіший спосіб — бібліотека sentence-transformers:

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(["hello world"])    # ← одна строчка

  Під капотом це PyTorch:
    AutoModel + AutoTokenizer + mean_pooling + normalize

  Зараз покажемо що саме відбувається під капотом ↓
""")


# ==============================================================
# РІВЕНЬ 2: HuggingFace AutoModel — контроль над пулінгом
# ==============================================================
print(f"{'=' * 65}")
print("РІВЕНЬ 2: AutoModel + ручний пулінг (що під капотом)")
print("=" * 65)
print("""
  Коли потрібен цей рівень:
    • Кастомний пулінг (не mean, а CLS-token або weighted)
    • Модель не підтримується SentenceTransformer
    • Потрібно бачити attention weights або hidden states
""")

from transformers import AutoModel, AutoTokenizer

MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model_hf = AutoModel.from_pretrained(MODEL).to(device)
model_hf.eval()  # ОБОВ'ЯЗКОВО — вимикаємо dropout

def mean_pooling(hidden_states, attention_mask):
    """Усереднюємо token embeddings з урахуванням padding."""
    mask = attention_mask.unsqueeze(-1).float()        # (B, T, 1)
    summed = (hidden_states * mask).sum(dim=1)          # (B, D)
    counts = mask.sum(dim=1).clamp(min=1e-9)            # (B, 1)
    return summed / counts                               # (B, D)

def embed_hf(texts):
    encoded = tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors='pt').to(device)
    with torch.inference_mode():                         # ОБОВ'ЯЗКОВО — без графу
        outputs = model_hf(**encoded)
    pooled = mean_pooling(outputs.last_hidden_state, encoded['attention_mask'])
    return F.normalize(pooled, dim=-1)                   # L2 нормалізація

doc_emb = embed_hf(documents)
q_emb = embed_hf([query])

sims2 = (q_emb @ doc_emb.T).squeeze(0)
top3_2 = sims2.topk(3)

print(f"  Результати (мають збігатися з рівнем 1):")
for score, idx in zip(top3_2.values.tolist(), top3_2.indices.tolist()):
    print(f"    [{score:.3f}] {documents[idx]}")

print(f"""
  Що ми контролюємо на цьому рівні:
    • tokenizer(texts, max_length=128)     — як токенізувати
    • model(**encoded).last_hidden_state   — сирі вектори кожного токена
    • mean_pooling(...)                    — як агрегувати в один вектор
    • F.normalize(pooled, dim=-1)          — L2 нормалізація для cosine similarity
""")


# ==============================================================
# РІВЕНЬ 3: Чистий PyTorch — повний контроль
# ==============================================================
print(f"{'=' * 65}")
print("РІВЕНЬ 3: Чистий PyTorch (низький рівень)")
print("=" * 65)
print("""
  Коли потрібен цей рівень:
    • Дебаг — хочеш побачити shape кожного тензора
    • Оптимізація — кастомний батчінг, mixed precision
    • Fine-tuning — додаєш свій classification head
""")

# Крок за кроком — як під капотом
text = query
encoded = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=128).to(device)

print(f"  Вхід: \"{text}\"")
print(f"  Token IDs: {encoded['input_ids'][0].tolist()[:10]}... ({encoded['input_ids'].shape[1]} токенів)")
print(f"  Attention mask: {encoded['attention_mask'][0].tolist()[:10]}...")

with torch.inference_mode():
    outputs = model_hf(**encoded)

hidden = outputs.last_hidden_state  # (1, T, 384)
print(f"\n  Hidden states shape: {tuple(hidden.shape)}  = (batch, tokens, embedding_dim)")
print(f"  Кожен токен → вектор із {hidden.shape[2]} чисел")

# Різні стратегії пулінгу
cls_emb = hidden[:, 0, :]                                  # CLS token
mean_emb = mean_pooling(hidden, encoded['attention_mask'])  # Mean
max_emb = hidden.max(dim=1).values                          # Max

print(f"\n  Стратегії пулінгу (як зібрати один вектор з {hidden.shape[1]} токенів):")
print(f"    CLS token:  shape {tuple(cls_emb.shape)}  — перший токен (як у BERT)")
print(f"    Mean pool:  shape {tuple(mean_emb.shape)}  — середнє (стандарт для sentence-transformers)")
print(f"    Max pool:   shape {tuple(max_emb.shape)}  — максимум по кожному виміру")

# Порівняємо якість
for name, emb in [("CLS", cls_emb), ("Mean", mean_emb), ("Max", max_emb)]:
    emb_norm = F.normalize(emb, dim=-1)
    sim = (emb_norm @ doc_emb[0:1].T).item()
    print(f"    {name} similarity з першим документом: {sim:.3f}")


# ==============================================================
# PRODUCTION: батчінг і latency
# ==============================================================
print(f"\n{'=' * 65}")
print("PRODUCTION: батчінг і вимірювання latency")
print("=" * 65)

# Збільшимо корпус
big_corpus = documents * 50  # 500 документів
print(f"\n  Корпус: {len(big_corpus)} документів")

# Warmup
embed_hf(documents[:4])
embed_hf(documents[:4])
sync()

# One-by-one
sync()
t0 = time.perf_counter()
for doc in big_corpus:
    embed_hf([doc])
sync()
time_one = time.perf_counter() - t0

# Batched (різні розміри)
results = []
for bs in [1, 8, 32, 64, 128]:
    sync()
    t0 = time.perf_counter()
    for i in range(0, len(big_corpus), bs):
        embed_hf(big_corpus[i:i+bs])
    sync()
    elapsed = time.perf_counter() - t0
    dps = len(big_corpus) / elapsed
    results.append({'bs': bs, 'time': elapsed, 'dps': dps})

print(f"\n  {'batch':>6}  {'час':>8}  {'docs/s':>8}  {'speedup':>8}")
print(f"  {'-'*36}")
for r in results:
    speedup = r['dps'] / results[0]['dps']
    print(f"  {r['bs']:>6}  {r['time']:>7.2f}s  {r['dps']:>8.1f}  {speedup:>7.1f}x")

best = max(results, key=lambda r: r['dps'])
print(f"""
  Найкращий batch: {best['bs']}  ({best['dps']:.0f} docs/s)
  Найгірший: batch=1  ({results[0]['dps']:.0f} docs/s)
  Різниця: {best['dps']/results[0]['dps']:.0f}x

  Production math (500,000 документів):
    batch=1:   {500000 / results[0]['dps'] / 3600:.1f} годин
    batch={best['bs']}:  {500000 / best['dps'] / 3600:.1f} годин
""")


# ==============================================================
# ПОРІВНЯННЯ З OpenAI API
# ==============================================================
print(f"{'=' * 65}")
print("ПОРІВНЯННЯ: локальні embeddings vs OpenAI API")
print("=" * 65)
print(f"""
  ┌────────────────────┬──────────────────┬──────────────────┐
  │                    │ Локальна модель  │ OpenAI API       │
  ├────────────────────┼──────────────────┼──────────────────┤
  │ Модель             │ MiniLM-L6-v2     │ text-embed-3-sm  │
  │ Розмірність        │ 384              │ 1536             │
  │ Конфіденційність   │ Дані на сервері  │ Дані в хмарі     │
  │ Вартість 500K docs │ $0 (свій GPU)    │ ~$10             │
  │ Вартість 50M docs  │ $0               │ ~$1,000          │
  │ Latency            │ {1000/best['dps']:.1f} ms/doc        │ ~50 ms/doc (мережа) │
  │ Fine-tuning        │ Так (PyTorch)    │ Ні               │
  │ Offline            │ Так              │ Ні               │
  │ Якість (MTEB)      │ 56.3             │ 62.3             │
  └────────────────────┴──────────────────┴──────────────────┘

  Коли обирати локальну модель:
    ✓ Дані конфіденційні (медицина, фінанси, юриспруденція)
    ✓ Великий обсяг (мільйони документів — API дорого)
    ✓ Потрібен fine-tuning під домен
    ✓ Потрібна робота без інтернету

  Коли обирати API:
    ✓ Маленький обсяг (до 100K документів)
    ✓ Не хочеш підтримувати GPU інфраструктуру
    ✓ Потрібна найвища якість з коробки
""")


# ==============================================================
# ПІДСУМОК
# ==============================================================
print(f"{'=' * 65}")
print("ЧЕКЛИСТ: локальні embeddings в production")
print("=" * 65)
print("""
  1. pip install sentence-transformers     # PyTorch під капотом
  2. model = SentenceTransformer('...')     # завантажити модель
  3. model.eval()                          # вимкнути dropout
  4. Батчінг — ЗАВЖДИ                      # 10-30x швидше
  5. torch.inference_mode()                # без memory leak

  Мінімальний production код (через HuggingFace):

    tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
    model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2').to('cuda')
    model.eval()

    @app.post("/embed")
    def embed(texts: list[str]):
        enc = tokenizer(texts, padding=True, truncation=True, return_tensors='pt').to('cuda')
        with torch.inference_mode():
            h = model(**enc).last_hidden_state
            pooled = mean_pooling(h, enc['attention_mask'])
            return F.normalize(pooled, dim=-1).tolist()
""")
