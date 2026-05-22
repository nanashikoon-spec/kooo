# Доскональное сравнение структуры: receipt_custom vs 29-01-26_18-35

**Вывод:** Бот проверяет структуру. Отклонение вызвано отличиями в BaseFont subset, /W, ToUnicode, /ID — не API.

## Запуск сравнения

```bash
python3 compare_structure_exhaustive.py receipt_custom.pdf база_чеков/vtb/СБП/29-01-26_18-35.pdf
```

---

## Сводка отличий

| Параметр | receipt_custom (наш) | 29-01-26_18-35 (эталон) | Совпадает |
|----------|----------------------|--------------------------|-----------|
| Размер файла | 9 433 bytes | 9 338 bytes | ✗ |
| PDF версия | 1.4 | 1.4 | ✓ |
| Номера объектов | 1–18 | 1–18 | ✓ |
| xref записей | 19 | 19 | ✓ |
| Content streams | 6 | 6 | ✓ |
| **Document /ID** | A796377C422974A8... | FD4CD29A5603C0C3... | ✗ |
| **CreationDate** | D:20260312132058 | D:20260312000456 | ✗ |
| Producer | openhtmltopdf.com | openhtmltopdf.com | ✓ |
| **BaseFont (subset)** | **AANHPC**+SFProDisplay-Regular | **AAWJPC**+SFProDisplay-Regular | ✗ |
| **/W массив** | len=364, hash=d58e40... | len=382, hash=3173d0... | ✗ |
| ToUnicode (obj 12) | len 1340, 9 CID только в A, 12 только в B | len 1382 | ✗ |
| Stream obj 1 | hash=84506592... | hash=b76f63a0... | ✗ |
| Stream obj 9 | hash=a0b94d46... | hash=7a3c7bef... | ✗ |
| Stream obj 13 | hash=6f2bd9a5... | hash=b4654c7a... | ✗ |
| Stream obj 17 | hash=bb91e6d0... | hash=8c895dd6... | ✗ |
| Stream obj 6, 18 | — | — | ✓ |
| MediaBox | [0,0,281.2125,43...] | то же | ✓ |

---

## Детальный анализ

### 1. Разные доноры → разная структура

**receipt_custom.pdf** собран из донора с шрифтом **AANHPC**+SFProDisplay-Regular.  
**29-01-26_18-35.pdf** использует **AAWJPC**+SFProDisplay-Regular.

Subset-тег задаётся при эмбеддинге шрифта и зависит от набора глифов. Разные доноры → разный subset → разная структура.

### 2. /W массив (ширины глифов)

- **Наш:** 364 байта, hash d58e40f6...
- **Эталон:** 382 байта, hash 3173d087...

/W задаёт ширины CID-глифов в CIDFontType2. Разные доноры имеют разные подмножества глифов и разные /W.

### 3. ToUnicode CMap (obj 12)

- В A: 9 CID только в нашем, 12 CID только в эталоне, 10 CID с разным маппингом.
- Разная длина: 1340 vs 1382 байт (decompressed).

### 4. Другие streams

| Объект | Назначение | Совпадает |
|--------|------------|-----------|
| 1 | ToUnicode/шрифт | ✗ |
| 6 | (общий) | ✓ |
| 9 | Content/ресурсы | ✗ |
| 13 | Content stream | ✗ (наш текст) |
| 17 | ToUnicode/CMap | ✗ |
| 18 | (общий) | ✓ |

### 5. Document ID и CreationDate

При патче генерируется новый /ID и обновляется CreationDate.

---

## Рекомендации: как приблизить структуру к эталону

### A. Использовать 29-01-26_18-35.pdf как донор

При генерации чека брать **именно** `база_чеков/vtb/СБП/29-01-26_18-35.pdf` как базовый PDF:

- совпадут BaseFont (AAWJPC), /W, ToUnicode;
- content stream будет отличаться (текст полей) — это неизбежно при смене данных.

**Ограничение:** все символы (ФИО, банк, телефон) должны быть в CMap эталона 29-01-26_18-35.

### B. Не менять метаданные

```json
"update_id": false
```

и `keep_metadata=True`, чтобы сохранить Document /ID и CreationDate донора.

### C. Минимальный патч

Менять только нужные поля (сумма, ФИО и т.п.), не трогать:

- шрифты и их subset;
- ToUnicode;
- /W;
- структуру объектов.

---

## Чек-лист

1. [ ] Донор = 29-01-26_18-35.pdf
2. [ ] `keep_metadata=True` / `update_id: false`
3. [ ] Все символы целевого текста есть в CMap донора
4. [ ] Патч только content stream (текст), без замены шрифтов и CMap

---

## Как сгенерировать с донором 29-01-26

```bash
# В vtb_config.json: "update_id": false

python3 vtb_patch_from_config.py база_чеков/vtb/СБП/29-01-26_18-35.pdf
```

Результат будет использовать BaseFont AAWJPC, /W и ToUnicode эталона. Отличаться будет только content stream (текст полей) и размер файла (зависит от длины текста).
