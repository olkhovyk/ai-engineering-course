# Домашнє завдання 16: Notes MCP Server

Це домашнє завдання для уроку 16 про MCP, тобто Model Context Protocol.

Ідея проєкту: зробити локальний MCP-сервер для нотаток. Сервер працює через `stdio`, експортує інструменти для роботи з нотатками і ресурси для читання стану локального сховища.

## Що реалізовано

- MCP-сервер на Python з офіційним пакетом `mcp`.
- Транспорт: `stdio`.
- Локальне сховище: `data/notes.json`.
- Три інструменти:
  - `add_note(title, content, tags=None)`
  - `search_notes(query, tag=None, limit=10)`
  - `list_notes(limit=10)`
- Два ресурси:
  - `notes://all`
  - `notes://stats`

## Структура проєкту

```text
homework/
  server.py
  requirements.txt
  codex_mcp_config.example.toml
  claude_desktop_config.example.json
  data/
    notes.json
  examples/
```

## Встановлення

Команди треба запускати з папки:

```text
lesson 16 - mcp-model-context-protocol/homework
```

Створити і активувати virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Встановити залежності:

```powershell
pip install -r requirements.txt
```

Перевірити, що `server.py` не має синтаксичних помилок:

```powershell
python -m py_compile server.py
```

## Як підключити до Codex app

Приклад конфігурації лежить у файлі:

```text
codex_mcp_config.example.toml
```

Суть конфігу така:

```toml
[mcp_servers.notes]
command = "python"
args = [
  "C:\\Users\\ilya1\\Documents\\rd_projects\\ai-engineering-course\\lesson 16 - mcp-model-context-protocol\\homework\\server.py"
]

[mcp_servers.notes.env]
NOTES_DB_PATH = "C:\\Users\\ilya1\\Documents\\rd_projects\\ai-engineering-course\\lesson 16 - mcp-model-context-protocol\\homework\\data\\notes.json"
```

Для реального запуску краще замінити `python` на повний шлях до Python з `.venv`, наприклад:

```text
C:\Users\ilya1\Documents\rd_projects\ai-engineering-course\lesson 16 - mcp-model-context-protocol\homework\.venv\Scripts\python.exe
```

Тоді Codex буде запускати саме Python з цього домашнього завдання, а не випадковий глобальний Python з системи.

## Приклад для Claude Desktop

У вимогах домашнього завдання згадується Claude Desktop, тому приклад конфігу теж доданий:

```text
claude_desktop_config.example.json
```

У цьому рішенні основний фокус на Codex app, але формат Claude Desktop залишений як частина здачі.

## Інструменти MCP

### `add_note`

Створює нову нотатку.

Обов'язкові аргументи:

- `title`
- `content`

Необов'язковий аргумент:

- `tags`

Приклад запиту:

```text
Створи нотатку з назвою "MCP idea", текстом "Build a notes MCP server" і тегами ["course", "mcp"].
```

### `search_notes`

Шукає нотатки по тексту і, якщо треба, по тегу.

Обов'язковий аргумент:

- `query`

Необов'язкові аргументи:

- `tag`
- `limit`

Приклад запиту:

```text
Знайди мої нотатки про MCP.
```

### `list_notes`

Повертає останні нотатки.

Необов'язковий аргумент:

- `limit`

Приклад запиту:

```text
Покажи мої останні нотатки.
```

## Ресурси MCP

### `notes://all`

Повертає всі нотатки у форматі JSON.

### `notes://stats`

Повертає кількість нотаток, статистику по тегах і шлях до локального JSON-файлу.

## Приклади діалогів для скріншотів

Після підключення MCP-сервера треба зробити 3 скріншоти і покласти їх у папку `examples/`.

### 1. Створення нотатки

```text
Створи нотатку: назва "Lesson 16", текст "MCP lets AI hosts call external tools through a standard protocol", теги ["mcp", "course"].
```

### 2. Пошук нотаток

```text
Знайди мої нотатки про MCP.
```

### 3. Читання статистики

```text
Покажи статистику нотаток через MCP resource.
```

## Відомі обмеження

- Дані зберігаються у простому JSON-файлі, а не в SQLite або Postgres.
- Пошук простий: використовується перевірка, чи входить рядок у текст нотатки.
- Немає окремого UI: сервер розрахований на MCP host, наприклад Codex або Claude Desktop.
