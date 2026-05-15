# PROMPT_LOG — Лог работы с AI

> Реальный журнал взаимодействия с AI-инструментами во время выполнения
> лабораторной работы №12 (вариант 6 — CRM для отдела продаж).
> Заполнялся **по ходу** работы, а не в конце.

## Инструменты

- **Claude Code (`claude-opus-4-7`)** — основной AI-агент. Использовался для
  проектирования архитектуры, генерации моделей/схем/сервисов, написания
  тестов и code review.
- **Google Gemini 1.5 Flash** — подключён в CI как автоматический ревьюер
  пулл-реквестов (`.github/workflows/ai_review.yml`).

Все промпты на русском. Где AI ошибался — оставлены пометки «правки вручную».

---

## Задание 1 — Реализация веб-приложения

### Промпт 1.1 — проектирование моделей SQLAlchemy 2.0

**Инструмент:** Claude Code

**Промпт:**

> Ты — senior Python разработчик. Спроектируй SQLAlchemy 2.0 модели для CRM
> отдела продаж: User (с ролью admin/manager/sales_rep), Client, Deal,
> Contact, Task. Используй декларативный синтаксис `Mapped[]` /
> `mapped_column`, добавь `TimestampMixin` с `created_at`, `updated_at`
> (с `onupdate=func.now()`). Все enum-поля сделай через Python `enum.Enum` +
> `sa.Enum(MyEnum, name="...")`. Поле `Deal.amount` — строго `Decimal` /
> `Numeric(12, 2)`, никаких float. Связи через `relationship(lazy="selectin")`.

**Результат:** Сгенерировал 5 моделей + `base.py` с `TimestampMixin`.
Корректно расставил `ForeignKey` с `ondelete="CASCADE"` где нужно, и
`SET NULL` для `assigned_to`.

**Правки вручную:**
- В первой итерации Claude использовал `lazy="joined"` для `User.clients`,
  что приводило к избыточному JOIN при логине — поменял на `selectin`.
- Добавил явные `foreign_keys=[...]` в `relationship(...)` для случаев, где
  у одной модели несколько FK на одну и ту же таблицу (Task → User).

### Промпт 1.2 — generic BaseRepository

**Инструмент:** Claude Code

**Промпт:**

> Напиши `BaseRepository[ModelType]` (Generic) с async-методами
> `get(id)`, `get_multi(skip, limit)`, `create(data)`, `update(id, data)`,
> `delete(id)`, `count()`. Используй современный API SQLAlchemy 2.0:
> `select()`, `session.execute()`, `result.scalars().all()`. Никаких
> устаревших `session.query()`.

**Результат:** Базовый репозиторий из ~50 строк. Все методы
параметризованы через `TypeVar("ModelType", bound=Base)`.

**Правки вручную:** В `delete()` Claude сначала забыл сделать `flush()` —
вернул `True` до фактического удаления. Поправил.

### Промпт 1.3 — машина состояний воронки продаж

**Инструмент:** Claude Code

**Промпт:**

> Реализуй `DealService.transition_stage(deal_id, new_stage, user)` с
> машиной состояний воронки. Допустимые переходы:
> lead → qualified, qualified → proposal, proposal → negotiation,
> negotiation → won; из любой стадии до won можно уйти в lost; won и lost —
> терминальные. Недопустимый переход — HTTPException 400. Также добавь
> ownership-проверку: sales_rep может менять только свои сделки.

**Результат:** Сгенерировал `FUNNEL_TRANSITIONS: dict[DealStage, set[DealStage]]`
и метод `transition_stage`, который сначала валидирует владельца, потом
проверяет допустимость перехода.

**Правки вручную:** В первом варианте Claude разрешил переход из `won` в
`lost` (логика «отмена сделки»). Уточнил в промпте: «терминальные» —
значит никаких переходов вообще. Удалил `won` и `lost` из ключей словаря
с пустыми `set()`.

### Промпт 1.4 — JWT-аутентификация с ролями

**Инструмент:** Claude Code

**Промпт:**

> Сделай JWT-аутентификацию: `hash_password`/`verify_password` через
> `passlib[bcrypt]`, `create_access_token`/`decode_access_token` через
> `python-jose`. В `dependencies.py` сделай `get_current_user` (читает
> токен через `OAuth2PasswordBearer`, достаёт `sub`, грузит пользователя),
> и фабрику `require_role(*roles)` для проверки ролей.

**Результат:** `core/security.py` и `core/dependencies.py` написались
почти без правок. Использовали `pydantic-settings.BaseSettings` для
`SECRET_KEY` — из `.env`, не хардкод.

**Правки вручную:** Был дубликат `get_db` в `database.py` и `dependencies.py` —
оставил один в `database.py`, реэкспортировал. Иначе тесты с
`app.dependency_overrides[get_db]` начинали работать непредсказуемо.

---

## Задание 2 — Code Review сгенерированного кода

### Промпт 2.1 — генерация намеренно плохого кода

**Инструмент:** Claude Code

**Промпт:**

> Сгенерируй файл `app/services/bad_deal.py` с **намеренно плохим** кодом
> для упражнения по code review. В файле должны быть как минимум 8 разных
> проблем разных уровней: 3 critical (float для денег, SQL-инъекция через
> f-string, отсутствие транзакции при связанных операциях), 2 high
> (хардкод секрета, KeyError при отсутствующей записи), 3 medium
> (магические числа, дублирование кода, функция >50 строк), несколько
> low (нет type hints, нарушение PEP 8, нет docstring). В шапке файла —
> большой комментарий что это намеренный антипример, исправленная версия
> в `deal_service.py`.

**Результат:** Получился файл из ~150 строк с 11 проблемами.
Комментарии вида `# CRITICAL #N:`, `# HIGH #N:` и т.д. помогли потом
быстро написать отчёт.

**Правки вручную:** Claude сначала добавил `# noqa` и `# nosec` на каждой
строке, чтобы линтер «не ругался». Я убрал их с конкретных строк и
поставил две глобальные пометки в шапке файла — иначе теряется смысл:
именно эти проблемы должны быть видны статическим анализаторам.

### Промпт 2.2 — анализ и составление отчёта

**Инструмент:** Claude Code

**Промпт:**

> Проведи code review файла `app/services/bad_deal.py`. Найди все проблемы,
> классифицируй по уровням Critical/High/Medium/Low. На каждую проблему:
> номер строки, в чём суть, какой риск (что плохого случится), как
> исправить. Сформируй отчёт `docs/CODE_REVIEW_REPORT.md` с таблицами по
> уровням и 3-5 примерами «до/после».

**Результат:** Отчёт с 11 проблемами, ссылками на исправленную версию
(`deal_service.py`), 5 развёрнутых примеров «до/после» с пояснениями.

**Правки вручную:** В примере про SQL-инъекцию Claude изначально предложил
исправление через `text(...).bindparams(...)`. Заменил на пример из
реального `ClientRepository.search` (через ORM `select(Client).where(...)`),
чтобы привязать отчёт к нашему коду.

---

## Задание 4 — Интеграция ИИ в CI/CD

### Промпт 4.1 — CI workflow с 4 job

**Инструмент:** Claude Code

**Промпт:**

> Напиши `.github/workflows/ci.yml` для FastAPI + SQLAlchemy проекта.
> Четыре независимых job: lint (`ruff check` + `ruff format --check`),
> test (`pytest --cov=app --cov-fail-under=90` + upload в Codecov),
> security (`bandit -r app/ -ll --exclude app/services/bad_deal.py`),
> docker-build (`docker build -t crm-app:test .`). Триггеры — push и PR
> на main/master/develop. Python 3.12 с кэшем pip.

**Результат:** Готовый workflow на 4 параллельных job. Использует
`actions/setup-python@v5` с `cache: pip`.

**Правки вручную:** Изначально Claude не передавал `--exclude` в bandit —
тот падал на намеренно плохом коде в `bad_deal.py` и валил CI. Это
основная причина, по которой это правило прямо прописано в CLAUDE.md.

### Промпт 4.2 — AI review через Gemini API

**Инструмент:** Claude Code

**Промпт:**

> Напиши `.github/workflows/ai_review.yml`: при открытии или обновлении
> PR — взять `git diff` (ограничить 6000 символов), отправить в Google
> Gemini 1.5 Flash через REST API, опубликовать ответ как комментарий в PR.
> Промпт для Gemini — «senior Python разработчик, найди баги/уязвимости/
> проблемы производительности, отвечай на русском». Используй `secrets.GEMINI_API_KEY`.

**Результат:** Workflow с тремя шагами: collect diff (через
`git diff origin/$base_ref...HEAD`), call Gemini (через `curl` + `jq`),
post comment (через `actions/github-script@v7`).

**Правки вручную:**
- Добавил обработку пустого diff: если `git diff` ничего не вернул —
  пропустить шаги, не падать.
- Обернул JSON-ответ Gemini в `python3 -c "import json; ..."` вместо
  `jq -r`, потому что `jq` плохо справлялся с многострочным
  Markdown-выводом модели (терял переводы строк).
- Зафиксировал ключ в Settings → Secrets and variables → Actions →
  `GEMINI_API_KEY` (получен бесплатно на aistudio.google.com/apikey).

---

## Задание 7 — Unit-тесты с покрытием ≥ 90%

### Промпт 7.1 — conftest.py для async-тестов

**Инструмент:** Claude Code

**Промпт:**

> Напиши `tests/conftest.py` для FastAPI + SQLAlchemy 2.0 async-проекта.
> Тесты должны работать на in-memory SQLite (`sqlite+aiosqlite:///:memory:`)
> — без PostgreSQL. Фикстуры: `async_engine` (создаёт и удаляет таблицы),
> `session`, `client` (httpx AsyncClient + ASGITransport с переопределённым
> `get_db`). Плюс хелпер `register_and_login` и три фикстуры с готовыми
> заголовками: `admin_headers`, `manager_headers`, `sales_rep_headers`.
> Также `other_rep_headers` для тестов чужого доступа.

**Результат:** Рабочий conftest. `app.dependency_overrides[get_db] = ...`
переопределяет реальный DI на in-memory sqlite-сессию.

**Правки вручную:**
- Первая попытка тестов упала с `ValueError: greenlet library is required`.
  Добавил `greenlet>=3.0` в `pyproject.toml` — это транзитивная
  зависимость SQLAlchemy для async, на Python 3.14 не подтягивается
  автоматически.
- Вторая попытка упала на bcrypt: `password cannot be longer than 72 bytes`.
  Несовместимость свежего `bcrypt>=4.1` с `passlib`. Запинил `bcrypt<4.1`.

### Промпт 7.2 — тесты по модулям

**Инструмент:** Claude Code

**Промпт:**

> Сгенерируй pytest-тесты для роутера `app/api/v1/deals.py`. Покрой:
> создание сделки с Decimal amount, переход lead → qualified (200),
> переход lead → won (недопустимо, 400), полный путь qualified → ... → won,
> qualified → lost, попытку перейти из терминального состояния, фильтр
> по stage, ownership (sales_rep видит только свои), 404 для несуществующей,
> 403 для удаления sales_rep'ом, 204 для удаления admin'ом, проверку
> сохранения Decimal без потери точности.

**Результат:** 15 тестов на deals, все зелёные с первого прогона.

**Правки вручную:** В тесте `test_decimal_precision_preserved` Claude
сравнивал `body["amount"] == "0.10"` (строки). Поменял на сравнение
`Decimal(body["amount"]) == Decimal("0.10")` — ровно та проверка, ради
которой написан тест.

### Промпт 7.3 — добор покрытия до 90%+

**Инструмент:** Claude Code

**Промпт:**

> Запустил pytest с `--cov=app`. Текущее покрытие 87%. Не покрыты:
> `users.py` (роутер целиком), `analytics_service.py` (manager_stats),
> `task_service.py` (overdue). Добей до 90%+. Уделять внимание не
> отдельным строкам, а смысловым кейсам.

**Результат:** Добавил `tests/test_users.py` (6 тестов на CRUD
сотрудников и проверку ролей) + расширил `test_analytics.py` (тест
manager-stats только для admin, тест 403 для sales_rep'а).
Итоговое покрытие — **95.27%, 68 тестов**.

**Правки вручную:** В тесте `test_manager_stats_admin_only` Claude забыл
проверить, что manager тоже не имеет доступа (только admin). Добавил эту
строку — иначе тест проходил бы, даже если случайно открыть эндпоинт
менеджерам.

---

## Сводка

| Задание | Промптов | AI-сгенерировано | Правок вручную |
|---------|----------|------------------|----------------|
| 1 | 4 | ~85% кода | Lazy-loading, дубликат `get_db`, FK с несколькими `relationship` |
| 2 | 2 | 100% | Убрал лишние `# noqa` в `bad_deal.py`, переписал пример SQL-инъекции |
| 4 | 2 | ~95% | Добавил `--exclude bad_deal.py`, обработку пустого diff, парсинг через python3 |
| 7 | 3 | ~90% | Пин `bcrypt<4.1`, `greenlet`, точное сравнение Decimal |

Общий вывод: AI хорошо генерирует **стандартный шаблонный код** (CRUD,
схемы, репозитории, простые тесты), но **систематически промахивается** в:

1. **Бизнес-инвариантах** — FSM воронки, ownership-проверки, edge cases.
2. **Совместимости версий** — особенно при свежих Python/SQLAlchemy.
3. **Семантике тестов** — пишет «работающий», но не «проверяющий» тест.

Поэтому без code review результаты AI использовать нельзя.
