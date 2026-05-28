# Лабораторная работа №12 — CRM для отдела продаж

Студент: Соколовский Степан Васильевич
Группа: 221131
Лабораторная работа: №12
Вариант: 6 — CRM для отдела продаж
Сложность: Повышенная

Веб-приложение CRM для отдела продаж: управление клиентами, контактными
лицами, сделками (с воронкой продаж и машиной состояний), задачами и
аналитикой. Реализовано на FastAPI + SQLAlchemy 2.0 + PostgreSQL.

---

## 📋 Выполненные задания

Согласно методичке, для повышенной сложности обязательны задания **1, 2, 4, 7**:

- **Задание 1** — Полноценное веб-приложение с аутентификацией (JWT,
  ролевая модель: admin / manager / sales_rep), CRUD основной сущности
  (Client), 3+ связанных сущностей (Deal, Contact, Task), отчётами
  (`/analytics/funnel`, `/analytics/kpi`, `/analytics/manager-stats`)
  и правами доступа на уровне эндпоинтов.
- **Задание 2** — Code Review намеренно плохого кода в
  `app/services/bad_deal.py`. Отчёт: [`docs/CODE_REVIEW_REPORT.md`](docs/CODE_REVIEW_REPORT.md).
  Найдено **11 проблем** (Critical: 3, High: 2, Medium: 3, Low: 3),
  исправленная версия — `app/services/deal_service.py`.
- **Задание 4** — Интеграция ИИ в CI/CD. Два workflow:
  - [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — 4 параллельных
    job (lint / test / security / docker-build).
  - [`.github/workflows/ai_review.yml`](.github/workflows/ai_review.yml) —
    автоматическое AI-ревью на каждом PR через Google Gemini 1.5 Flash.
- **Задание 7** — Unit-тесты с покрытием **≥ 90%** (фактически **95.27%**,
  68 тестов). Отчёт: [`docs/COVERAGE_REPORT.txt`](docs/COVERAGE_REPORT.txt).

Задания 3, 5, 6, 8 — факультативные, не реализуются согласно методичке.

Лог взаимодействия с AI: [`PROMPT_LOG.md`](PROMPT_LOG.md).

---

## 🛠 Технологический стек

| Категория | Технологии |
|-----------|-----------|
| Язык | Python 3.12 |
| Веб-фреймворк | FastAPI ≥ 0.111 |
| ORM | SQLAlchemy 2.0 (async, `Mapped[]`/`mapped_column`) |
| СУБД | PostgreSQL 16 (production), SQLite + aiosqlite (тесты) |
| Драйвер БД | asyncpg |
| Миграции | Alembic 1.13+ (async env) |
| Валидация | Pydantic v2, pydantic-settings |
| Аутентификация | python-jose (JWT), passlib (bcrypt) |
| Тесты | pytest + pytest-asyncio + pytest-cov + httpx AsyncClient |
| Линтер | ruff |
| Безопасность | bandit |
| Контейнеризация | Docker (multi-stage) + docker-compose |
| CI/CD | GitHub Actions |
| AI Review | Google Gemini 1.5 Flash |

---

## 🏗 Архитектура

Классическая слоистая архитектура с разделением ответственности:

```
HTTP Request
   │
   ▼
API Layer  (app/api/v1/)     ← FastAPI роутеры: HTTP, валидация, авторизация
   │
   ▼
Service Layer (services/)    ← Бизнес-логика, FSM воронки, проверка ролей
   │
   ▼
Repository Layer (repos/)    ← Async CRUD, изоляция SQL-запросов
   │
   ▼
Model Layer (models/)        ← SQLAlchemy 2.0 ORM
   │
   ▼
PostgreSQL 16
```

---

## 📦 Предметная область

### Сущности и связи

- **User** (`admin` / `manager` / `sales_rep`) — ведёт клиентов, назначен на задачи.
- **Client** — компания-клиент, имеет несколько контактных лиц, сделок и задач.
- **Deal** — сделка, принадлежит клиенту, имеет стадию воронки и
  `amount: Decimal(12, 2)` (никогда float!).
- **Contact** — контактное лицо клиента.
- **Task** — задача, связана с пользователем (исполнителем), опционально
  с клиентом и сделкой.

### Машина состояний воронки продаж (`Deal.stage`)

```
lead → qualified → proposal → negotiation → won
                                          ↘
                                            lost (из любой нетерминальной стадии)
```

Недопустимые переходы (например, `lead → won`) возвращают `HTTP 400`.
Реализация — `app/services/deal_service.py`, словарь `FUNNEL_TRANSITIONS`.

### Ролевая модель

| Роль | Права |
|------|-------|
| `admin` | Полный доступ, управление пользователями, все отчёты |
| `manager` | Все клиенты/сделки/задачи команды, статистика воронки |
| `sales_rep` | Только свои клиенты/сделки/задачи |

---

## 🚀 Запуск

### Вариант 1: Docker Compose (рекомендуется)

```bash
cp .env.example .env
docker compose up --build
```

Приложение будет доступно на http://localhost:8000, Swagger UI — на
http://localhost:8000/docs.

### Вариант 2: Локально

Требуется Python 3.12+ и работающий PostgreSQL (или используйте
in-memory SQLite, поменяв `DATABASE_URL`).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

# Применить миграции
alembic upgrade head

# (Опционально) Заполнить демо-данными
python -m scripts.seed_db

# Запустить
uvicorn app.main:app --reload
```

---

## 🌐 API эндпоинты

Полная интерактивная документация — на `/docs` (Swagger UI) и `/redoc`.

### Auth `/api/v1/auth`
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/auth/register` | Регистрация (любой) |
| POST | `/auth/login` | JWT-токен (form-data) |
| GET | `/auth/me` | Профиль текущего пользователя |

### Clients `/api/v1/clients`
| Метод | Путь | Описание | Роль |
|-------|------|----------|------|
| GET | `/clients/` | Список (sales_rep — свои, manager/admin — все) | любой |
| GET | `/clients/search?q=` | Поиск по компании/контакту | любой |
| POST | `/clients/` | Создать | любой |
| GET | `/clients/{id}` | Данные + контакты + сделки | любой |
| PUT | `/clients/{id}` | Обновить | владелец / admin |
| DELETE | `/clients/{id}` | Удалить | admin |

### Deals `/api/v1/deals`
| Метод | Путь | Описание | Роль |
|-------|------|----------|------|
| GET | `/deals/` | Список с фильтром по stage/assigned_to | любой |
| POST | `/deals/` | Создать сделку | любой |
| GET | `/deals/{id}` | Данные сделки | любой |
| PUT | `/deals/{id}` | Обновить | владелец / manager / admin |
| PATCH | `/deals/{id}/stage` | Переход по воронке | владелец / manager / admin |
| DELETE | `/deals/{id}` | Удалить | admin |

### Contacts `/api/v1/contacts`
| Метод | Путь | Описание | Роль |
|-------|------|----------|------|
| GET | `/contacts/?client_id=` | Список | любой |
| POST | `/contacts/` | Добавить | владелец клиента / admin |
| PUT | `/contacts/{id}` | Обновить | владелец / admin |
| DELETE | `/contacts/{id}` | Удалить | admin |

### Tasks `/api/v1/tasks`
| Метод | Путь | Описание | Роль |
|-------|------|----------|------|
| GET | `/tasks/` | Мои задачи (или все для admin/manager) | любой |
| GET | `/tasks/overdue` | Просроченные задачи | любой |
| POST | `/tasks/` | Создать | любой |
| PUT | `/tasks/{id}` | Обновить | владелец / admin |
| PATCH | `/tasks/{id}/status` | Изменить статус | владелец / admin |
| DELETE | `/tasks/{id}` | Удалить | admin |

### Users `/api/v1/users`
| Метод | Путь | Описание | Роль |
|-------|------|----------|------|
| GET | `/users/` | Список сотрудников | admin, manager |
| GET | `/users/{id}` | Данные сотрудника | admin, manager |
| PATCH | `/users/{id}/deactivate` | Деактивировать | admin |

### Analytics `/api/v1/analytics`
| Метод | Путь | Описание | Роль |
|-------|------|----------|------|
| GET | `/analytics/funnel` | Кол-во и сумма сделок по стадиям | manager, admin |
| GET | `/analytics/kpi` | Win rate, средний чек, средний цикл | manager, admin |
| GET | `/analytics/manager-stats` | Статистика по менеджерам | admin |

---

## 🧪 Тестирование

Тесты используют **in-memory SQLite** (aiosqlite) — PostgreSQL для прогона
тестов не нужен.

```bash
# Запустить все тесты
pytest -v

# С покрытием (порог >= 90%)
pytest --cov=app --cov-report=term-missing --cov-fail-under=90

# Сохранить отчёт о покрытии
pytest --cov=app --cov-report=term-missing 2>&1 | tee docs/COVERAGE_REPORT.txt
```

**Итог:**
- 68 тестов
- 95.27% покрытие
- порог 90% перекрыт

Структура тестов:
- `tests/test_auth.py` (11 тестов) — регистрация/логин/me/деактивация
- `tests/test_clients.py` (13 тестов) — CRUD, ownership, поиск
- `tests/test_deals.py` (15 тестов) — CRUD, FSM воронки, точность Decimal
- `tests/test_contacts.py` (8 тестов) — CRUD, проверка прав
- `tests/test_tasks.py` (9 тестов) — CRUD, overdue, смена статуса
- `tests/test_analytics.py` (6 тестов) — funnel, KPI, manager-stats
- `tests/test_users.py` (6 тестов) — управление сотрудниками

---

## 🤖 CI/CD

При каждом push/PR на ветки `main`/`master`/`develop` GitHub Actions
запускает четыре независимых job:

1. **lint** — `ruff check` + `ruff format --check`
2. **test** — `pytest` с порогом покрытия 90% + загрузка отчёта в Codecov
3. **security** — `bandit -r app/ -ll --exclude app/services/bad_deal.py`
4. **docker-build** — `docker build`

Дополнительно при открытии/обновлении PR срабатывает **AI Code Review**:
diff отправляется в Gemini 1.5 Flash, ответ постится комментарием в PR.

---

## 📁 Структура проекта

```
lab12_crm/
├── app/
│   ├── api/v1/              # FastAPI роутеры
│   ├── core/                # config, security, dependencies, database
│   ├── models/              # SQLAlchemy 2.0 модели
│   ├── repositories/        # Async-репозитории
│   ├── schemas/             # Pydantic v2 схемы
│   ├── services/            # Бизнес-логика
│   │   ├── deal_service.py  # FSM воронки + Decimal
│   │   └── bad_deal.py      # ⚠️ намеренно плохой код для задания 2
│   └── main.py
├── alembic/                 # Async-миграции
├── tests/                   # 68 тестов
├── scripts/seed_db.py       # Демо-данные
├── docs/
│   ├── CODE_REVIEW_REPORT.md
│   └── COVERAGE_REPORT.txt
├── .github/workflows/       # CI + AI review
├── Dockerfile               # Multi-stage
├── docker-compose.yml       # Postgres + app
├── alembic.ini
├── pyproject.toml
├── PROMPT_LOG.md            # Лог работы с AI
└── README.md
```

