# Система координат ВТБ СБП

**Зафиксировано.** Логика выравнивания верна, не менять без обоснования.

## Основной принцип

- **Правый столбец** (дата, плательщик, получатель, телефон, банк, счёт, ID операции): последняя буква каждого поля на одной вертикали с буквой «о» в слове «Выполнено» — это **wall**.

## Формулы

### 1. Правый столбец (wall)

```
tm_x = wall - real_text_width
```

где `real_text_width` — ширина TJ в units, считаемая из:
- `/W` массива CIDFontType2 (CID → width)
- Кернинга из TJ (например `-16.66667` между глифами)

Если `old_units > 0` и `new_units > 0`:
```
scale = (wall - tm_x_old) / old_units
new_x = wall - new_units * scale
```

Fallback (если units не считаются):
```
new_x = wall - n_glyphs * pts
```
где `pts` — из `_fallback_pts()` или из донора.

### 2. Центрирование шапки

ФИО под «Исходящий перевод СБП» центрируется по ширине:

```
center_heading = (50 + wall) / 2  # или из layout_overrides
new_x = center_heading - (new_units * scale) / 2
```

### 3. Сумма

Сумма всегда в **font-size 13.5pt**:

```
new_x_amt = wall - new_units * (13.5 / 1000.0)
```

## Источники значений

| Параметр | Источник |
|----------|----------|
| wall | vtb_sber_reference (донор) или layout_config.json / layout_overrides.json |
| center_heading | Аналогично |
| Y координаты | vtb_sber_reference (raw) или vtb_sbp_layout (y.date, y.payer и т.д.) |
| y_tolerance | layout_overrides.y_tolerance (по умолчанию 0.15) |

## Кернинг по полям

| Поле | Керн |
|------|------|
| Дата, плательщик, получатель, телефон, банк, счёт, opid | -16.66667 |
| ФИО под заголовком (центрировано) | -21.42857 |
| Сумма | -11.11111 |

## Ключевые модули

- `vtb_patch_from_config.py` — патч, замена полей, расчёт tm_x
- `vtb_sbp_layout.py` — layout_config + layout_overrides, Y и wall
- `vtb_test_generator.py` — `tm_x_touch_wall(wall, n_glyphs, pts)`
