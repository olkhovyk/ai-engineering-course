# Мультиагентна система синхронізації HR та транспортної логістики розподільчого центру

## Бізнес-проблема

Фури прибувають на розподільчий центр, а персоналу для розвантаження немає. Це спричиняє простій автотранспорту та фінансові втрати. Система координує графіки змін персоналу з графіком прибуття фур через 4 автономних агенти в реальному часі.

## Технології

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (async), Alembic
- **Frontend:** Angular 17, TypeScript, SCSS
- **Database:** PostgreSQL 16
- **Agent Messaging:** Redis 7 (pub/sub)
- **Containerization:** Docker Compose

## Архітектура мультиагентної системи

| Агент | Функція |
|---|---|
| **Coordinator** | Центральний оркестратор: маршрутизує повідомлення, вирішує конфлікти, призначає персонал |
| **Alert** | Виявляє нестачу персоналу при прибутті фур, створює попередження |
| **ShiftPlanner** | Оптимізує графіки змін під навантаження, викликає додаткових працівників |
| **Forecasting** | Прогнозує навантаження на основі історичних даних (moving average) |

Агенти спілкуються через Redis pub/sub канали та працюють як async-задачі всередині FastAPI.

## Швидкий старт

```bash
# Клонувати репозиторій
git clone <repo-url>
cd course-project-1

# Запустити всі сервіси
docker-compose up --build

# Відкрити браузер
# Frontend: http://localhost:4200
# Backend API: http://localhost:8000/docs
```

## Демо-сценарії

1. Відкрити **Simulation** (http://localhost:4200/simulation)
2. Обрати сценарій:
   - **Normal Day** — 20 фур рівномірно, достатньо персоналу
   - **Peak Overload** — 40 фур о 12:00, нестача персоналу
   - **Late Arrivals** — фури запізнюються на 1-2 години
3. Натиснути кнопки "+1 hour", "+2 hours" для просування часу
4. Спостерігати зміни на **Dashboard**:
   - Доки змінюють статус (free → occupied)
   - Фури з'являються в черзі
   - Агенти логують рішення (вкладка Agent Log)
   - Сповіщення при нестачі персоналу

## Структура проекту

```
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app + agent startup
│   │   ├── agents/          # Multi-agent system
│   │   ├── models/          # SQLAlchemy ORM
│   │   ├── routers/         # REST API
│   │   ├── services/        # Business logic
│   │   └── seed/            # Demo data
│   └── alembic/             # DB migrations
└── frontend/
    └── src/app/
        ├── core/            # Services, models
        └── features/        # Dashboard, schedule, simulation
```

## API

Документація: http://localhost:8000/docs (Swagger UI)

Основні ендпоінти:
- `GET /api/v1/dashboard/summary` — зведена статистика
- `POST /api/v1/simulation/scenario/{name}` — завантажити сценарій
- `POST /api/v1/simulation/tick?minutes=15` — просунути час
- `GET /api/v1/agents/logs` — лог рішень агентів

## Формула розрахунку потреби персоналу

- **1 вантажник** на кожні 10 палет
- **1 водій навантажувача** на кожні 20 палет
