# Сводка: генерация чеков и прохождение проверки

## Почему gen_random / gen_custom могут не проходить проверку

1. **Document ID** — при `keep_metadata=False` генерируется полностью новый /ID (MD5 от содержимого). Бот помечает такие чеки как подделку. Нужно: `keep_metadata=True` + изменить **1 символ** в hex.

2. **CreationDate** — в patch_from_values при `keep_metadata=False` ставится `datetime.now()`, а не дата из чека. Даты расходятся. Нужно: явно вызывать `update_creation_date` с датой, совпадающей с текстом в чеке.

3. **База доноров** — `find_donor`/`find_all_donors` берут из `receipt_index.json` (163 чека СБП). Проверка идёт по символам (chars), не по качеству патча. Разные доноры имеют разную структуру (payer/recipient mapping, Y-координаты). Случайный донор может дать кривой результат.

4. **Доноры** — только в `база_чеков/vtb/СБП`. gen_verified_receipt берёт доноров оттуда.

## Что сделано

| Файл | Назначение |
|------|------------|
| **CHECK_VERIFICATION_RULES.md** | Зафиксированные правила: что можно менять, чтобы чек прошёл |
| **gen_verified_receipt.py** | Генератор, использующий проверенных доноров и критерии прохождения |

## Использование

```bash
# Базовый вариант (дефолтные данные)
python3 gen_verified_receipt.py receipt.pdf

# С параметрами
python3 gen_verified_receipt.py out.pdf --payer "Иван Иванов И." --recipient "Пётр Петров П." --amount 5000 --phone "+7 (900) 123-45-67"

# Явный донор
python3 gen_verified_receipt.py out.pdf --donor "13-03-26_00-00_4.pdf" --amount 10000
```

## Доноры

Все доноры — в `база_чеков/vtb/СБП`. Добавляй туда новые PDF, индексируй через `python3 receipt_db.py build`.
