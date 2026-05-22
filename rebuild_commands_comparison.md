# Сравнение команд rebuild_pdf

## Новая команда (с учётом всех изменений)

```bash
python3 - <<'PY'
import random
import string
import subprocess

random_suffix = "".join(random.choice(string.digits) for _ in range(16))
new_account = "4081" + random_suffix

cmd = [
    "python3", "rebuild_pdf.py", "input ru.pdf", "Квитанция (20).pdf",
    "--donor-pdf", "donor.pdf",
    "--strict-forensic",
    "--font-alias-from-input",
    "--replace", f"40817810980480002476={new_account}",
    "--replace", "C422402260356995=C422402260934672",
    "--replace", "10=5 000",
    "--replace", "79003517080=79097790757",
    "--replace", "ВТБ=Озон Банк (Ozon)",
    "--replace", "Александр Евгеньевич Ж=Владимир Данилович В.",
    "--replace", "24.02.2026 10:38:28=02.03.2026 11:14:32",
    "--replace", "24.02.2026 13:39=02.03.2026 11:19",
    "--replace", "A60550738283070H0000020011700501=A60550738283070H0000020011900653",
]

print("Generated account:", new_account)
print("Running:", " ".join(cmd))
subprocess.run(cmd, check=True)
PY
```

**Что изменено:**
- Добавлено `--font-alias-from-input` — имя шрифта в PDF берётся из input (font000000002f4db77f и т.п.)
- Убрано `--copy-input-metadata` — теперь по умолчанию **включено**
- Убрано `--match-input-pdf-version` — теперь по умолчанию **включено**
- По умолчанию включаются: копирование метаданных, совпадение версии PDF, попытка сохранить исходные шрифты (для Type0 используется Tahoma с алиасом из input)

---

## Старая команда (как было до изменений)

```bash
python3 - <<'PY'
import random
import string
import subprocess

random_suffix = "".join(random.choice(string.digits) for _ in range(16))
new_account = "4081" + random_suffix

cmd = [
    "python3", "rebuild_pdf.py", "input ru.pdf", "Квитанция (20).pdf",
    "--donor-pdf", "donor.pdf",
    "--strict-forensic",
    "--copy-input-metadata",
    "--match-input-pdf-version",
    "--replace", f"40817810980480002476={new_account}",
    "--replace", "C422402260356995=C422402260934672",
    "--replace", "10=5 000",
    "--replace", "79003517080=79097790757",
    "--replace", "ВТБ=Озон Банк (Ozon)",
    "--replace", "Александр Евгеньевич Ж=Владимир Данилович В.",
    "--replace", "24.02.2026 10:38:28=02.03.2026 11:14:32",
    "--replace", "24.02.2026 13:39=02.03.2026 11:19",
    "--replace", "A60550738283070H0000020011700501=A60550738283070H0000020011900653",
]

print("Generated account:", new_account)
print("Running:", " ".join(cmd))
subprocess.run(cmd, check=True)
PY
```

**Чем отличалась:**
- Обязательно указывались `--copy-input-metadata` и `--match-input-pdf-version`
- Не было `--font-alias-from-input`
- В PDF использовалось имя "Tahoma Regular" вместо исходного
