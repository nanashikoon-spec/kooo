#!/bin/bash
# Оптимальный вариант: компактный файл (~437 KB), структура как AM.
# Время подставляется текущее по МСК
NOW_MSK=$(TZ='Europe/Moscow' date '+%d.%m.%Y %H:%M:%S')
DATE_MSK=$(TZ='Europe/Moscow' date '+%d.%m.%Y %H:%M')
CREATION=$(TZ='Europe/Moscow' date '+%Y-%m-%d %H:%M')

# AM_1772658254522 — бот распознаёт как Альфа-Банк (шрифт EGGZCV).
# --subset-fonts: уменьшает файл с ~437KB до ~60KB (как эталон). Без TJS — только RUR.
# --native-match: content как у AM (CID-патч), font/ToUnicode от AM — файл ~59 KB как родной.
python3 rebuild_pdf.py "input ru.pdf" "Квитанция 15.pdf" \
  --match-pdf "AM_1772658254522.pdf" \
  --match-pdf-metadata-only \
  --native-match \
  --subset-fonts \
  --creation-date "$CREATION" \
  --replace "40817810980480002476=40817810980487823350" \
  --replace "C422402260356995=C160403262149539" \
  --replace "A60550738283070H0000020011700501=A60631903485960P0000000011700501" \
  --replace "10 RUR=50 000 RUR" \
  --keep-input-producer \
  --replace "24.02.2026 10:38:28=$NOW_MSK" \
  --replace "24.02.2026 13:39=$DATE_MSK"
