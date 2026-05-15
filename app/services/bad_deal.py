# ruff: noqa
# nosec
"""
ВНИМАНИЕ: Это намеренно плохой код, сгенерированный AI на ранней итерации.
Файл сохранён для задания 2 (Code Review) — см. docs/CODE_REVIEW_REPORT.md.
Исправленная версия находится в app/services/deal_service.py.
НЕ ИСПОЛЬЗОВАТЬ В ПРОДАКШЕНЕ.
"""

from sqlalchemy import select

from app.models.deal import Deal
from app.models.task import Task


# === CRITICAL #1: float для денежных вычислений ===
# Использование float приводит к потерям точности при округлении.
# Пример: 0.1 + 0.2 != 0.3
def calc_commission(amount, rate=0.15):
    return amount * rate


# === CRITICAL #2: SQL-инъекция через f-string ===
# Прямая подстановка пользовательского ввода в SQL-запрос.
# Атакующий может передать name="' OR 1=1 --" и получить всех клиентов.
async def find_client(db, name):
    result = await db.execute(
        f"SELECT * FROM clients WHERE company_name = '{name}'"
    )
    return result.fetchall()


# === CRITICAL #3: Отсутствие транзакции при связанных операциях ===
# Если db.commit() упадёт, deal.stage уже изменён в памяти (и может быть
# отправлен другим запросом), а task так и не будет создан.
# Должно быть обёрнуто в async with session.begin().
async def close_deal_and_create_task(db, deal_id, task_data):
    deal = await db.get(Deal, deal_id)
    deal.stage = "won"
    await db.flush()
    task = Task(**task_data)
    db.add(task)
    await db.commit()
    return deal, task


# === HIGH #4: Хардкод секрета в исходном коде ===
# Секрет попадает в git-историю, утекает в логи и публичные репозитории.
# Должен браться из переменных окружения или хранилища секретов.
JWT_SECRET = "supersecret123"  # noqa: S105


# === HIGH #5: Отсутствие обработки ошибок — KeyError ===
# Если deal с указанным ID не найден, словарь не содержит этот ключ —
# KeyError проваливается наверх как 500 Internal Server Error вместо 404.
async def get_deal_info(db, deal_id):
    deals = await db.execute(select(Deal))
    d = {x.id: x for x in deals.scalars()}
    return d[deal_id]


# === MEDIUM #6: Магические числа без констант ===
# Пороги и ставки разбросаны по коду, изменение требует поиска по проекту.
# Должны быть именованные константы (TIER_LARGE_THRESHOLD и т.п.).
def commission_rate(deal):
    if deal.amount > 1000000:
        rate = 0.05
    elif deal.amount > 500000:
        rate = 0.08
    else:
        rate = 0.12
    return rate


# === MEDIUM #7: Дублирование кода (copy-paste) ===
# Одинаковая логика валидации повторена в трёх местах —
# любое изменение придётся вносить везде.
def validate_deal_amount_v1(amount):
    if amount is None:
        raise ValueError("amount is None")
    if amount < 0:
        raise ValueError("amount must be positive")
    if amount > 99999999:
        raise ValueError("amount too large")
    return True


def validate_deal_amount_v2(amount):
    if amount is None:
        raise ValueError("amount is None")
    if amount < 0:
        raise ValueError("amount must be positive")
    if amount > 99999999:
        raise ValueError("amount too large")
    return True


def validate_deal_amount_v3(amount):
    if amount is None:
        raise ValueError("amount is None")
    if amount < 0:
        raise ValueError("amount must be positive")
    if amount > 99999999:
        raise ValueError("amount too large")
    return True


# === MEDIUM #8: Функция > 50 строк, делает слишком много ===
# Парсит вход, валидирует, считает комиссию, обновляет статус, шлёт уведомление,
# логирует — нарушает Single Responsibility Principle, невозможно тестировать
# по частям.
async def process_deal(db, deal_id, action, payload, tmp=None, x=None):
    deal = await db.get(Deal, deal_id)
    if deal is None:
        return None
    if action == "close":
        deal.stage = "won"
        if deal.amount > 1000000:
            rate = 0.05
        elif deal.amount > 500000:
            rate = 0.08
        else:
            rate = 0.12
        commission = deal.amount * rate
        tmp = commission
        x = deal.amount - commission
        deal.notes = f"closed, commission={tmp}, net={x}"
        await db.flush()
    elif action == "reopen":
        deal.stage = "negotiation"
        await db.flush()
    elif action == "lose":
        deal.stage = "lost"
        deal.notes = "lost"
        await db.flush()
    elif action == "update_amount":
        if payload is None:
            return None
        if "amount" not in payload:
            return None
        deal.amount = payload["amount"]
        if deal.amount > 1000000:
            rate = 0.05
        elif deal.amount > 500000:
            rate = 0.08
        else:
            rate = 0.12
        tmp = deal.amount * rate
        deal.notes = f"new commission={tmp}"
        await db.flush()
    elif action == "delete":
        await db.delete(deal)
        await db.commit()
    await db.commit()
    return deal


# === LOW #9: нет type hints ни в одной функции выше ===
# === LOW #10: нарушение PEP 8 — имена d, tmp, x ===
# === LOW #11: нет документации (docstring) на публичных функциях ===
