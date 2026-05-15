# Code Review Report: `app/services/bad_deal.py`

## Методология

Проведён ручной анализ файла `app/services/bad_deal.py` с использованием
Claude Code (модель `claude-opus-4-7`) в качестве ассистента-ревьюера.
Дополнительно запускались статические анализаторы:

- `ruff check app/services/bad_deal.py` — стиль и базовые ошибки
- `bandit app/services/bad_deal.py` — безопасность (SQL-инъекции, хардкод
  секретов, слабые криптопримитивы)

Найдено **11 проблем** по 4 уровням критичности.
Исправленная версия лежит в `app/services/deal_service.py`.

---

## Проблемы

### 🔴 Critical

| # | Строка | Проблема | Риск | Исправление |
|---|--------|----------|------|-------------|
| 1 | ~19 | `float` для денежных вычислений (`amount * rate`) | Финансовые потери при округлении; накопление погрешности на больших объёмах | Использовать `Decimal` из модуля `decimal`, ставки задавать как `Decimal("0.15")` |
| 2 | ~26 | SQL-инъекция через f-string в `find_client` | Компрометация БД, утечка/удаление данных | Параметризованные запросы (`text(...).bindparams(...)`) или ORM `select(Client).where(...)` |
| 3 | ~37 | Связанные операции (`deal.stage = "won"` + создание Task) без транзакции | Inconsistent state: сделка закрыта, задача не создана при сбое | `async with session.begin():` обёртка вокруг всех мутаций |

### 🟠 High

| # | Строка | Проблема | Риск | Исправление |
|---|--------|----------|------|-------------|
| 4 | ~50 | Хардкод `JWT_SECRET = "supersecret123"` в исходниках | Утечка секрета в git, в логи, в публичные репозитории | Читать из `pydantic-settings` (`.env`, переменные окружения, vault) |
| 5 | ~58 | `get_deal_info` падает с `KeyError` при отсутствующем deal | HTTP 500 вместо 404, плохой UX, маскирует ошибки | Явная проверка `if deal is None: raise HTTPException(404)` |

### 🟡 Medium

| # | Строка | Проблема | Риск | Исправление |
|---|--------|----------|------|-------------|
| 6 | ~67 | Магические числа `1000000`, `500000`, `0.05`, `0.08`, `0.12` | Невозможно понять смысл, изменения требуют поиска по проекту | Именованные константы: `TIER_LARGE_THRESHOLD`, `COMMISSION_RATE_LARGE` и т.д. |
| 7 | ~80 | Дублирование `validate_deal_amount_v1/v2/v3` (copy-paste) | Изменения требуется вносить в 3 местах; неизбежен расхождение | Вынести в одну функцию-валидатор или в Pydantic-схему (`Field(ge=0, le=...)`) |
| 8 | ~110 | Функция `process_deal` > 50 строк, делает 5+ вещей (SRP) | Невозможно тестировать по частям, высокая когнитивная сложность | Разбить: `_close()`, `_reopen()`, `_lose()`, `_update_amount()`, `_delete()`; диспетчер по `action` |

### 🟢 Low

| # | Строка | Проблема | Риск | Исправление |
|---|--------|----------|------|-------------|
| 9 | весь файл | Отсутствие type hints | Хуже читаемость, отсутствует поддержка IDE/`mypy` | Добавить аннотации (`Decimal`, `AsyncSession`, `Deal | None`) |
| 10 | ~110+ | Имена `d`, `tmp`, `x` — нарушение PEP 8 | Снижает читаемость | Осмысленные имена: `deals_by_id`, `commission`, `net_amount` |
| 11 | весь файл | Нет docstring у публичных функций | Затруднена документация и автогенерация | Краткий docstring с описанием контракта (что принимает, что возвращает, что бросает) |

---

## Итог

| Уровень | Кол-во |
|---------|--------|
| 🔴 Critical | 3 |
| 🟠 High | 2 |
| 🟡 Medium | 3 |
| 🟢 Low | 3 |
| **Всего** | **11** |

Минимальный порог методички (5 проблем) перекрыт в 2 раза.
Исправленная версия: [`app/services/deal_service.py`](../app/services/deal_service.py).

---

## Примеры исправлений

### Проблема 1: float → Decimal

**Что сгенерировал ИИ (в `bad_deal.py`):**
```python
def calc_commission(amount, rate=0.15):
    return amount * rate
```

**В чём проблема:**
`float` использует двоичное представление и теряет точность на десятичных
дробях. На сумме сделок 1 000 000 ₽ ошибка может составить несколько копеек,
а на портфеле из сотен сделок — десятки рублей в месяц. Финансовая отчётность
такое не прощает.

**Как исправил (в `deal_service.py`):**
```python
from decimal import Decimal

COMMISSION_RATE_SMALL = Decimal("0.12")
COMMISSION_RATE_MEDIUM = Decimal("0.08")
COMMISSION_RATE_LARGE = Decimal("0.05")


def calc_commission(amount: Decimal) -> Decimal:
    if amount > TIER_LARGE_THRESHOLD:
        rate = COMMISSION_RATE_LARGE
    elif amount > TIER_MEDIUM_THRESHOLD:
        rate = COMMISSION_RATE_MEDIUM
    else:
        rate = COMMISSION_RATE_SMALL
    return amount * rate
```

Параллельно `Deal.amount` объявлен как `Mapped[Decimal]` с типом
`sa.Numeric(12, 2)` — никаких `float` ни в модели, ни в схеме, ни в сервисе.

---

### Проблема 2: SQL-инъекция → параметризация / ORM

**Что сгенерировал ИИ:**
```python
async def find_client(db, name):
    await db.execute(
        f"SELECT * FROM clients WHERE company_name = '{name}'"
    )
```

**В чём проблема:**
Атакующий передаёт `name = "' OR 1=1 --"` и получает весь список клиентов;
варианты с `; DROP TABLE clients --` могут уничтожить данные.

**Как исправил (в `ClientRepository.search`):**
```python
from sqlalchemy import or_, select

async def search(self, query: str) -> list[Client]:
    pattern = f"%{query}%"
    stmt = select(Client).where(
        or_(
            Client.company_name.ilike(pattern),
            Client.contact_person.ilike(pattern),
        )
    ).order_by(Client.id)
    result = await self.session.execute(stmt)
    return list(result.scalars().all())
```

ORM генерирует параметризованный SQL; `query` уходит как bind-параметр и
никогда не интерпретируется как часть SQL-выражения.

---

### Проблема 3: транзакция для связанных операций

**Что сгенерировал ИИ:**
```python
async def close_deal_and_create_task(db, deal_id, task_data):
    deal = await db.get(Deal, deal_id)
    deal.stage = "won"
    await db.flush()
    task = Task(**task_data)
    db.add(task)
    await db.commit()
```

**В чём проблема:**
Между `flush()` и `commit()` любая ошибка (например, нарушение FK при
создании task) оставит deal в состоянии `won`, но без сопровождающей задачи.
В CRM это значит, что менеджеру не назначат follow-up по только что
выигранной сделке.

**Как исправил:**
В сервисном слое используется `async with session.begin():` для атомарных
операций, а в `transition_stage` сам переход и валидация выполняются в
рамках одной транзакции:

```python
async def transition_stage(
    self, deal_id: int, new_stage: DealStage, user: User
) -> Deal:
    deal = await self.get_or_404(deal_id, user)
    allowed = FUNNEL_TRANSITIONS.get(deal.stage, set())
    if new_stage not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition: {deal.stage.value} -> {new_stage.value}",
        )
    updated = await self.repo.update(deal.id, {"stage": new_stage})
    return updated
```

Также добавлена **машина состояний** (`FUNNEL_TRANSITIONS`), которая не даёт
сделать недопустимый переход вроде `lead → won`.

---

### Проблема 4: хардкод секрета → pydantic-settings

**Было:**
```python
JWT_SECRET = "supersecret123"
```

**Стало (`app/core/config.py`):**
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
```

В продакшене `SECRET_KEY` подкладывается через переменную окружения
(или `.env`, который в `.gitignore`).

---

### Проблема 5: KeyError → HTTPException 404

**Было:**
```python
async def get_deal_info(db, deal_id):
    deals = await db.execute(select(Deal))
    d = {x.id: x for x in deals.scalars()}
    return d[deal_id]
```

**Стало (`DealService.get_or_404`):**
```python
async def get_or_404(self, deal_id: int, user: User) -> Deal:
    deal = await self.repo.get(deal_id)
    if deal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )
    if user.role == UserRole.sales_rep and deal.assigned_to != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your deal",
        )
    return deal
```

Дополнительно: точечная выборка одной записи через `session.get` вместо
загрузки всей таблицы в память.
