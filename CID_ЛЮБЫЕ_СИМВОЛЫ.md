# CID-патч с любыми символами: как это возможно

## Проблема

- **CID-патч** даёт маленький файл (~9 KB), но требует, чтобы все символы уже были в CMap и шрифте donor'а.
- **copy_font_cmap** (подмена шрифта из другого чека) ломает отображение: у разных PDF разные CID→GID, даже при одинаковом ToUnicode.
- **content_stream_replace** (PyMuPDF + Arial) даёт корректный текст, но файл ~450–800 KB.

Цель: **CID + малый размер + любые символы**.

---

## Как устроен CID-шрифт в PDF

Цепочка отображения:

```
Байты в content stream  →  CIDs (Encoding/CMap)  →  GIDs (CIDToGIDMap)  →  глифы в шрифте
         ↑                        ↑                         ↑
    что мы пишем            ToUnicode (только          внутренняя структура
    в TJ/Tj                 для копирования текста)   шрифта
```

- **ToUnicode** — только для извлечения/копирования текста, на рендеринг не влияет.
- **CIDToGIDMap** — отображает CID в индекс глифа (GID) в шрифте.
- Если CID 0x0410 ведёт к GID, где в шрифте нет «А», будет пусто или мусор.

---

## Почему Identity «ломает» (ПОЧЕМУ_БОТ_ОТКЛОНЯЕТ.md)

При добавлении Identity в ToUnicode (`CID = Unicode`, т.е. CID 0x0410 для «А»):

- ToUnicode меняется, но **шрифт остаётся прежним**.
- CIDToGIDMap по-прежнему отображает CID 0x0410 в какой-то GID.
- В subset-шрифте глиф «А» обычно лежит в GID 5, 10 и т.п., а не в 1040.
- В итоге CID 0x0410 указывает на неверный глиф → «квадратики» или пусто.

---

## Варианты решения

### 1. Donor с полным набором символов (оптимально)

**Идея:** Использовать donor, где уже есть все нужные буквы (А–Я, а–я, М, Б, Л и т.д.).

- Не трогаем шрифт и CIDToGIDMap.
- Делаем только CID-патч по content stream.
- Файл остаётся ~9 KB.

**Как:** Собрать «универсальный» donor — чек того же формата (ВТБ, тот же layout), в котором встречаются все нужные символы. Использовать его как единственный источник для CID-патча.

---

### 2. Homoglyph (уже есть в cid_patch_amount.py)

**Идея:** Заменять отсутствующие кириллические буквы на похожие латинские (А→A, М→M, Б→B и т.д.).

- Не меняем шрифт и ToUnicode.
- Используем уже существующие глифы.
- Ограничение: не все буквы имеют визуально похожие латинские аналоги (р, м, и и т.д.).

---

### 3. Новый CID-шрифт из Arial subset (fontTools + pyHanko)

**Идея:** Создать свой CID-шрифт с нужными символами и корректным CIDToGIDMap.

1. **fontTools** — subset Arial только для нужных символов:
   ```bash
   pyftsubset /path/to/Arial.ttf --text="Арман Мелсикович Б." --output-file=arial_subset.otf
   ```

2. **pyHanko GlyphAccumulator** — встраивание subset в PDF:
   - `feed_string("Арман Мелсикович Б.")` — помечает нужные глифы.
   - `embed_subset()` — встраивает CID-шрифт с корректным CIDToGIDMap.

3. В content stream — добавить новый шрифт (например, `/F2`) и заменить нужный текст на вывод через этот шрифт.

**Плюсы:** Любые символы, малый размер (только нужные глифы).  
**Минусы:** Нужно модифицировать content stream (добавить переключение шрифта, новые TJ/Tj), что сложнее простого CID-патча.

---

### 4. Donor из того же источника (тот же font engine)

**Идея:** Если оба чека сгенерированы одним приложением (например, одним и тем же клиентом ВТБ), у них может быть одинаковая структура шрифта и CID→GID.

- Проверить: `pdffonts 04-02-26.pdf` и `pdffonts 07-03-26.pdf` — совпадают ли имена шрифтов, encoding, subset.
- Если да — copy_font_cmap может сработать, т.к. CID→GID совпадает.
- Если нет — подмена шрифта даст «пустой» или искажённый текст.

---

## Рекомендация

1. **Сначала:** Найти donor того же формата (Входящий перевод СБП) с максимальным набором букв. Использовать его для CID-патча без copy_font_cmap.
2. **Если символов не хватает:** Расширить homoglyph в `_CYRILLIC_FALLBACK` (cid_patch_amount.py) для дополнительных пар.
3. **Если нужны «любые» символы без ограничений:** Реализовать путь с fontTools + pyHanko: subset Arial → новый CID-шрифт → встраивание и замена текста в content stream.

---

## Ссылки

- [Understanding PDF CIDFonts, CMaps, and GIDs](https://stackoverflow.com/questions/75576696/understanding-pdf-cidfonts-cmaps-and-gids-best-practices) — цепочка character codes → CIDs → GIDs.
- [fontTools subset](https://fonttools.readthedocs.io/en/latest/subset.html) — `--text=`, `--unicodes=` для subset.
- [pyHanko GlyphAccumulator](https://pyhanko.readthedocs.io/en/0.2.0/api-docs/pyhanko.pdf_utils.font.html) — `feed_string()`, `embed_subset()`.
- [PDF Font Subsetting](https://www.pdf-tools.com/pdf-knowledge/font-subsetting-how-it-works-when-use/) — как работает subset.
