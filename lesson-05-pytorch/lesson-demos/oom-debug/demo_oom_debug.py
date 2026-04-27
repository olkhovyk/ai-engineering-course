"""
Demo: Діагностика OOM — реальний сценарій AI-інженера.

Сценарій:
  Компанія будує пошук по внутрішній документації (RAG).
  1. Спочатку хотіли OpenAI embeddings → не можна, дані конфіденційні (медичні записи)
  2. Взяли sentence-transformers/all-MiniLM-L6-v2 → запускаємо локально через PyTorch
  3. Написали сервіс, запустили → OOM error через 10 хвилин
  4. Як прочитати помилку, знайти причину, виправити?

Запуск: python demo_oom_debug.py
"""
import torch
import torch.nn as nn
import time

device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")

# ==============================================================
# КОНТЕКСТ: чому ми тут
# ==============================================================
print("=" * 65)
print("РЕАЛЬНИЙ КЕЙС: RAG для медичної документації")
print("=" * 65)
print("""
  Задача: пошук по 500,000 медичних записів (конфіденційні дані).

  Крок 1: OpenAI text-embedding-ada-002
    ✗ Відхилено compliance-командою.
    Причина: дані не можуть залишати наші сервери (HIPAA/GDPR).

  Крок 2: Локальна модель sentence-transformers/all-MiniLM-L6-v2
    ✓ Дані залишаються на нашому сервері.
    ✓ PyTorch під капотом — працює на нашому GPU.
    Пишемо embedding-сервіс → FastAPI + PyTorch.

  Крок 3: Запускаємо в проді → через 10 хвилин:
    ╔══════════════════════════════════════════════════════╗
    ║  RuntimeError: CUDA out of memory.                  ║
    ║  Tried to allocate 256.00 MiB                       ║
    ║  (GPU 0; 24.00 GiB total capacity;                  ║
    ║   23.14 GiB already allocated)                      ║
    ╚══════════════════════════════════════════════════════╝

  Що це? Чому? Як виправити? Давайте розберемо.
""")

print(f"device: {device}")
print(f"{'='*65}\n")


def get_memory_mb():
    if device == "mps":
        return torch.mps.current_allocated_memory() / 1e6
    elif device == "cuda":
        return torch.cuda.memory_allocated() / 1e6
    return 0


# Проста модель — як embedding сервіс у проді
class EmbeddingModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(512, 2048),
            nn.GELU(),
            nn.Linear(2048, 2048),
            nn.GELU(),
            nn.Linear(2048, 512),
        )
        self.drop = nn.Dropout(0.1)

    def forward(self, x):
        return self.drop(self.layers(x))


model = EmbeddingModel().to(device)
params = sum(p.numel() for p in model.parameters())
print(f"Model: {params:,} parameters ({params * 4 / 1e6:.1f} MB)")
print(f"{'='*65}\n")


# ==============================================================
# БАГ 1: Забули model.eval() — dropout активний
# ==============================================================
print("БАГ 1: model.eval() забули")
print("-" * 40)

x = torch.randn(8, 512, device=device)

# Показуємо ефект dropout напряму
drop = nn.Dropout(0.3)  # 30% нейронів вимикаються

print("Dropout при model.train() — один вектор, 5 викликів:")
sample = torch.tensor([0.5, 0.3, 0.8, 0.1, 0.6, 0.9, 0.2, 0.7], device=device)
for i in range(5):
    dropped = drop(sample)  # dropout активний
    vals = [f"{v:.2f}" for v in dropped.tolist()]
    zeros = sum(1 for v in dropped.tolist() if v == 0)
    print(f"  запуск {i+1}: [{', '.join(vals)}]  ({zeros} обнулених)")

# Тепер повна модель
model.train()  # dropout ON
results_train = []
for i in range(5):
    with torch.no_grad():
        out = model(x)
    results_train.append(out[0, :3].cpu().tolist())
diffs = sum(1 for i in range(1, 5) if results_train[i] != results_train[0])
print(f"\n  Повна модель (model.train), 5 запусків:")
print(f"  Різних результатів: {diffs} з 4  (на деяких GPU dropout фіксує seed)")
print(f"  >>> ПРОБЛЕМА: в реальному сервісі з тисячами запитів — шум накопичується!")

model.eval()  # dropout OFF
results_eval = []
for i in range(5):
    with torch.no_grad():
        out = model(x)
    results_eval.append(out[0, :3].cpu().tolist())

print(f"\n  model.eval() — ті самі 5 запусків:")
for i, r in enumerate(results_eval):
    vals = [f"{v:>7.4f}" for v in r]
    print(f"  запуск {i+1}: [{', '.join(vals)}]")
all_same_eval = all(r == results_eval[0] for r in results_eval)
print(f"  Результати однакові? {all_same_eval}")
print(f"  >>> FIX: model.eval() вимикає dropout → детерміновані результати")


# ==============================================================
# БАГ 2: Забули torch.no_grad() — пам'ять тече
# ==============================================================
print(f"\n{'='*65}")
print("БАГ 2: torch.no_grad() забули — memory leak")
print("-" * 40)

model.eval()
batch = torch.randn(32, 512, device=device)
n_requests = 50

# --- БЕЗ no_grad (баг) ---
if device != "cpu":
    torch.mps.empty_cache() if device == "mps" else torch.cuda.empty_cache()

mem_start = get_memory_mb()
print(f"\nБЕЗ torch.no_grad() — {n_requests} запитів:")

tensors_alive = []
for i in range(n_requests):
    out = model(batch)  # граф обчислень зберігається!
    tensors_alive.append(out)  # результати тримають граф у пам'яті
    if (i + 1) % 10 == 0:
        mem = get_memory_mb()
        print(f"  запит {i+1:>3}: memory = {mem:.1f} MB (+{mem - mem_start:.1f} MB)")

mem_no_grad_off = get_memory_mb()
has_graph = tensors_alive[0].grad_fn is not None
print(f"  grad_fn = {tensors_alive[0].grad_fn}")
print(f"  >>> Кожен результат тримає computation graph у пам'яті!")

del tensors_alive
if device != "cpu":
    torch.mps.empty_cache() if device == "mps" else torch.cuda.empty_cache()

# --- З no_grad (правильно) ---
mem_start2 = get_memory_mb()
print(f"\nЗ torch.no_grad() — ті самі {n_requests} запитів:")

tensors_clean = []
for i in range(n_requests):
    with torch.no_grad():
        out = model(batch)
    tensors_clean.append(out)
    if (i + 1) % 10 == 0:
        mem = get_memory_mb()
        print(f"  запит {i+1:>3}: memory = {mem:.1f} MB (+{mem - mem_start2:.1f} MB)")

has_graph_clean = tensors_clean[0].grad_fn is not None
print(f"  grad_fn = {tensors_clean[0].grad_fn}")
print(f"  >>> Без графу — пам'ять не росте!")

del tensors_clean


# ==============================================================
# БАГ 3: Швидкість — граф = overhead
# ==============================================================
print(f"\n{'='*65}")
print("БАГ 3: torch.no_grad() = швидше")
print("-" * 40)

model.eval()
batch = torch.randn(64, 512, device=device)

def sync():
    if device == "cuda": torch.cuda.synchronize()
    elif device == "mps": torch.mps.synchronize()

# Warmup
for _ in range(5):
    with torch.no_grad():
        model(batch)
sync()

# Без no_grad
sync()
t0 = time.perf_counter()
for _ in range(100):
    _ = model(batch)
sync()
time_with_graph = time.perf_counter() - t0

# З no_grad
sync()
t0 = time.perf_counter()
for _ in range(100):
    with torch.no_grad():
        _ = model(batch)
sync()
time_no_graph = time.perf_counter() - t0

print(f"  100 forward passes БЕЗ no_grad:  {time_with_graph*1000:.1f} ms")
print(f"  100 forward passes З no_grad:    {time_no_graph*1000:.1f} ms")
print(f"  Різниця: {time_with_graph/time_no_graph:.2f}x")


# ==============================================================
# БАГ 4: Симуляція OOM у продакшні
# ==============================================================
print(f"\n{'='*65}")
print("БАГ 4: Симуляція production OOM")
print("-" * 40)

big_model = nn.Sequential(
    nn.Linear(1024, 4096), nn.GELU(),
    nn.Linear(4096, 4096), nn.GELU(),
    nn.Linear(4096, 1024),
).to(device).eval()

big_batch = torch.randn(128, 1024, device=device)

print(f"\nСценарій: embedding-сервіс, 128 запитів/батч, великі embedding")
print(f"Програміст забув torch.no_grad() і model.eval()...\n")

big_model.train()  # BAD
mem_before = get_memory_mb()

try:
    results = []
    for step in range(30):
        out = big_model(big_batch)  # no eval, no no_grad
        results.append(out)
        mem = get_memory_mb()
        bar = "█" * int((mem - mem_before) / 5)
        if (step + 1) % 5 == 0:
            print(f"  запит {step+1:>3}: {mem:.0f} MB {bar}")
except RuntimeError as e:
    if "out of memory" in str(e).lower() or "MPS" in str(e):
        print(f"\n  💥 OOM на запиті {step+1}!")
    else:
        raise

del results
if device != "cpu":
    torch.mps.empty_cache() if device == "mps" else torch.cuda.empty_cache()

print(f"\n  FIX — додаємо 2 рядки:")
print(f"    big_model.eval()              # вимикає dropout")
print(f"    with torch.inference_mode():  # вимикає граф обчислень")

big_model.eval()
mem_before2 = get_memory_mb()
with torch.inference_mode():
    for step in range(30):
        out = big_model(big_batch)
        if (step + 1) % 10 == 0:
            mem = get_memory_mb()
            print(f"  запит {step+1:>3}: {mem:.0f} MB — стабільно ✓")


# ==============================================================
# ЯК ЧИТАТИ OOM ПОМИЛКУ
# ==============================================================
print(f"\n{'='*65}")
print("ЯК ЧИТАТИ OOM ПОМИЛКУ")
print("=" * 65)
print("""
  Типова помилка на CUDA GPU:
  ┌─────────────────────────────────────────────────────────────┐
  │ RuntimeError: CUDA out of memory.                           │
  │ Tried to allocate 256.00 MiB                                │
  │ (GPU 0; 24.00 GiB total capacity;                           │
  │  23.14 GiB already allocated;                                │
  │  128.00 MiB free; 23.50 GiB reserved)                       │
  └─────────────────────────────────────────────────────────────┘

  Як це читати:
  • "Tried to allocate 256 MiB"    → PyTorch хотів ще 256 MB
  • "24 GiB total"                 → загальна пам'ять GPU
  • "23.14 GiB already allocated"  → вже зайнято 23 з 24 GB!
  • "128 MiB free"                 → залишилось лише 128 MB

  Типова помилка на Apple MPS:
  ┌─────────────────────────────────────────────────────────────┐
  │ RuntimeError: MPS backend out of memory.                    │
  │ Tried to allocate 512.00 MiB.                               │
  │ Current allocated memory: 7.89 GiB.                         │
  └─────────────────────────────────────────────────────────────┘

  Чому "already allocated" такий великий?
  Кожен запит БЕЗ no_grad() зберігає computation graph.
  100 запитів × 80 MB графу = 8 GB зайвої пам'яті.
  Модель сама займає 90 MB. Решта — сміття від графів.

  3 кроки дебагу:
  1. Перевір model.eval()              → чи вимкнений dropout?
  2. Перевір torch.no_grad()           → чи є grad_fn на виході?
     result = model(x)
     print(result.grad_fn)             → None = ок, інше = баг
  3. Перевір batch size                → зменши якщо OOM навіть з no_grad
""")

# ==============================================================
# ПОВЕРНЕННЯ ДО КЕЙСУ
# ==============================================================
print(f"{'='*65}")
print("ПОВЕРНЕННЯ ДО КЕЙСУ: медичний RAG-сервіс")
print("=" * 65)
print("""
  Що було:
    • OpenAI embeddings ✗ (compliance)
    • Локальна модель sentence-transformers ✓
    • OOM через 10 хвилин роботи

  Що знайшли:
    • Розробник забув model.eval() і torch.no_grad()
    • Кожен з 500 запитів/хв зберігав computation graph
    • За 10 хвилин: 5000 × 8 MB = 40 GB графів → OOM

  Що виправили:
    + model.eval()                    # 1 рядок
    + with torch.inference_mode():   # 1 рядок
    Пам'ять стабільна на 95 MB. Сервіс працює 24/7.

  Скільки часу зайняв фікс: 30 секунд.
  Скільки часу зайняв дебаг: 3 години (бо не знали куди дивитись).
  Після цього уроку: 5 хвилин.
""")

# ==============================================================
# ПІДСУМОК
# ==============================================================
print(f"{'='*65}")
print("ЧЕКЛИСТ ДЛЯ PRODUCTION INFERENCE")
print("=" * 65)
print("""
  1. model.eval()              — ЗАВЖДИ після завантаження моделі
                                 Без нього: dropout рандомізує результати

  2. torch.no_grad()           — обгортає КОЖЕН inference виклик
     або torch.inference_mode()  Без нього: пам'ять тече, OOM о 3-й ночі

  3. torch.inference_mode()    — строгіша версія no_grad (PyTorch 2.0+)
                                 Трохи швидше, рекомендовано для проду

  Мінімальний шаблон:

    model = load_model()
    model.eval()                          # один раз

    @app.post("/predict")
    def predict(request):
        with torch.inference_mode():      # кожен запит
            result = model(request.data)
        return result
""")
