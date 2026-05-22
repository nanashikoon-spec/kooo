# Полная инструкция по деплою бота

Бот использует **long polling** (getUpdates), работает на Python 3.10+. Почти без внешних зависимостей (PyMuPDF опционален для базы чеков).

---

## Шаг 0: Подготовка

### 1. Получить токен бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram.
2. Отправьте `/newbot` или выберите существующего бота через `/mybots`.
3. Скопируйте токен вида `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`.

### 2. Узнать свой User ID (для ALLOWED_USER_IDS)

1. Отправьте любое сообщение боту [@userinfobot](https://t.me/userinfobot).
2. Скопируйте число из поля **Id** (например, `1445265832`).
3. Добавьте все ID через запятую: `1445265832,7076663447`.

**Без ALLOWED_USER_IDS бот будет доступен всем** — не оставляйте пустым в продакшене.

### 3. Шаблон выписки Альфа (`выписка_жуков_177414_СБП_одна_операция.pdf`)

Основной донор — **`выписка_жуков_177414_СБП_одна_операция.pdf`** (в корне репозитория или `~/Downloads/`). После `git pull` файл из репо должен быть на сервере.

- Если файла нет — выполните в каталоге проекта: `python3 build_statement_zhukov_177414.py` (нужен `AM_1774146329068.pdf` в репо или `~/Downloads/`).
- Скрипты вроде `task2_statements.py` могут быть заточены под **AM_1774134591446.pdf** — это отдельный эталон для проверок, не обязательно совпадает с шаблоном бота.
- Выписки «с нуля» и правки — в **`bot_standalone.py`**. **`bot.py`** (python-telegram-bot) использует другой поток и **не** содержит эти правки.

**Обновление на VPS после пуша в GitHub:**

```bash
cd /путь/к/cheketop   # каталог клона
git pull origin main
# systemd:
sudo systemctl restart cheketop    # имя сервиса как у вас в unit-файле
# или процесс вручную:
# pkill -f bot_standalone.py
# nohup python3 bot_standalone.py > bot.log 2>&1 &
```

Проверка, что запущен нужный процесс: `ps aux | grep bot_standalone` (не `bot.py`).

---

## Способ 1: Docker (рекомендуется)

### Локальный запуск

```bash
# Перейти в папку проекта
cd /путь/к/чекетоп

# Создать .env (или передать переменные вручную)
echo 'TELEGRAM_BOT_TOKEN=ваш_токен' >> .env
echo 'ALLOWED_USER_IDS=1445265832,7076663447' >> .env

# Сборка образа
docker build -t cheketop .

# Запуск в фоне
docker run -d --name cheketop --env-file .env cheketop

# Проверить логи
docker logs -f cheketop
```

### Через docker-compose

```bash
# Создать .env с TELEGRAM_BOT_TOKEN и ALLOWED_USER_IDS
nano .env   # или любой редактор

# Запуск
docker-compose up -d

# Остановка
docker-compose down
```

### Обновление бота (Docker)

```bash
# Остановить контейнер
docker stop cheketop && docker rm cheketop

# Пересобрать образ (после git pull или изменений)
docker build -t cheketop .

# Запустить снова
docker run -d --name cheketop --env-file .env cheketop
```

---

## Способ 2: Render.com (бесплатно)

Render даёт бесплатный Web Service. Сервис «засыпает» через 15 мин без запросов — используйте UptimeRobot для пинга.

### Пошагово

1. Залейте проект на GitHub (если ещё не сделано):
   ```bash
   git init
   git add .
   git commit -m "Initial"
   git remote add origin https://github.com/ВАШ_ЛОГИН/cheketop.git
   git push -u origin main
   ```

2. Перейдите на [render.com](https://render.com) → Sign Up (через GitHub).

3. **New** → **Web Service**.

4. Подключите репозиторий (Connect account → выберите репозиторий).

5. Настройте сервис:
   - **Name:** `cheketop` (любое)
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements-bot.txt || true`
   - **Start Command:** `python3 run_render.py`
   - **Instance Type:** Free

6. В **Environment** добавьте переменные:
   - `TELEGRAM_BOT_TOKEN` = ваш токен
   - `ALLOWED_USER_IDS` = `1445265832,7076663447`
   - `PORT` = оставьте пустым (Render задаёт сам)

7. Нажмите **Create Web Service**.

8. Дождитесь деплоя (1–2 мин). В логах должно быть: `Listening on 0.0.0.0:10000`, `Бот запущен`.

9. Подключите UptimeRobot (чтобы Render не засыпал):
   - [uptimerobot.com](https://uptimerobot.com) → Add Monitor
   - URL: `https://ваш-сервис.onrender.com/healthz`
   - Interval: 5 minutes
   - Alert contacts: Email/Telegram

10. Добавьте переменные watchdog (Render → Environment):
   - `WATCHDOG_TIMEOUT_SEC` = `180` (через сколько секунд без heartbeat перезапускать сервис)
   - `WATCHDOG_CHECK_INTERVAL_SEC` = `10` (интервал проверки watchdog)

11. Проверка health/metrics:
   - `https://ваш-сервис.onrender.com/healthz` → JSON со статусом `ok/degraded`
   - `https://ваш-сервис.onrender.com/metrics` → uptime/restart_count/heartbeat
   - Если `/healthz` возвращает 503, watchdog завершит процесс, Render поднимет новый инстанс

---

## Способ 3: Bothost (рекомендуется для РФ)

Bothost — хостинг для Telegram-ботов в РФ, бесплатно 1 бот 24/7.

### Пошагово

1. Регистрация на [bothost.ru](https://www.bothost.ru).

2. **Создать бота** → подключите GitHub-репозиторий.

3. Укажите команду запуска:
   ```
   python3 receipt_db.py build; python3 bot_standalone.py
   ```
   (индекс пересоберётся при каждом старте)

4. В настройках бота добавьте переменные:
   - `TELEGRAM_BOT_TOKEN`
   - `ALLOWED_USER_IDS`

5. Нажмите **Старт**. Бот будет работать постоянно.

---

## Способ 4: VPS (Oracle Cloud, DigitalOcean и др.)

Подходит для полного контроля. Пример — Oracle Cloud Free Tier (бесплатно навсегда).

### Подключение к серверу

```bash
ssh ubuntu@ВАШ_IP
```

### Установка и запуск

```bash
# Обновление системы
sudo apt update && sudo apt install -y python3 python3-pip git

# Клонирование (если репо на GitHub)
cd ~
git clone https://github.com/ВАШ_ЛОГИН/cheketop.git
cd cheketop

# Зависимости
pip3 install -r requirements-bot.txt

# Переменные окружения
export TELEGRAM_BOT_TOKEN="ваш_токен"
export ALLOWED_USER_IDS="1445265832,7076663447"

# Сборка индекса базы чеков
python3 receipt_db.py build

# Запуск в фоне
nohup python3 bot_standalone.py > bot.log 2>&1 &

# Проверить, что бот запущен
ps aux | grep bot_standalone
tail -f bot.log
```

### Автозапуск при перезагрузке (systemd)

Создайте файл `/etc/systemd/system/cheketop.service`:

```ini
[Unit]
Description=Cheketop Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/cheketop
Environment="TELEGRAM_BOT_TOKEN=ваш_токен"
Environment="ALLOWED_USER_IDS=1445265832,7076663447"
ExecStart=/usr/bin/python3 bot_standalone.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable cheketop
sudo systemctl start cheketop
sudo systemctl status cheketop
```

---

## Способ 5: Railway

1. [railway.app](https://railway.app) → **Start a New Project** → **Deploy from GitHub**.
2. Выберите репозиторий.
3. **Variables** → добавьте `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_IDS`.
4. Railway подхватит `Procfile` и запустит `run_render.py`.

**Бесплатно:** $5 кредит в месяц.

---

## Способ 6: Koyeb

1. [koyeb.com](https://koyeb.com) → **Create App**.
2. Git deploy → подключите репозиторий.
3. **Run command:** `pip install -r requirements-bot.txt 2>/dev/null; python3 receipt_db.py build; python3 bot_standalone.py`
4. Secrets → `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_IDS`.

---

## Переменные окружения

| Переменная | Описание | Обязательно |
|------------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Токен от @BotFather | Да |
| `ALLOWED_USER_IDS` | ID через запятую (123,456). Пусто = доступ всем | Рекомендуется |
| `HTTPS_PROXY` | Прокси (если Telegram заблокирован) | Нет |
| `PORT` | Для run_render.py (Render задаёт сам) | Только Render |
| `WATCHDOG_TIMEOUT_SEC` | Порог stale heartbeat (сек) | Рекомендуется на Render |
| `WATCHDOG_CHECK_INTERVAL_SEC` | Частота проверок watchdog (сек) | Опционально |

---

## Обновление после изменений в коде

### Git-based (Render, Bothost, Railway, Koyeb)

```bash
git add .
git commit -m "Описание изменений"
git push origin main
```

Деплой запустится автоматически.

### VPS / Docker

```bash
git pull
python3 receipt_db.py build   # если менялась база чеков
# Перезапустить бота (systemd, docker restart и т.д.)
```

---

## Обновление базы чеков (база_чеков)

**Через бота:** Главное меню → «Проверка базы» → «➕ СБП» / «➕ ВТБ→ВТБ» / «➕ Альфа» → отправьте PDF.  
Либо загрузите файлы вручную в папки и нажмите **«Обновить индекс»**.

**Через CLI:**
```bash
python3 receipt_db.py build
python3 receipt_db.py add чек.pdf vtb_sbp
```

---

## Проверка после деплоя

1. Откройте бота в Telegram.
2. Отправьте `/start` — должно появиться главное меню.
3. Если нет ответа:
   - Проверьте логи на хостинге.
   - Убедитесь, что `TELEGRAM_BOT_TOKEN` верный.
   - Проверьте `ALLOWED_USER_IDS`, если задан — ваш ID должен быть в списке.

---

## Быстрый старт (Docker, кратко)

```bash
docker build -t cheketop .
docker run -d --name cheketop \
  -e TELEGRAM_BOT_TOKEN="ваш_токен" \
  -e ALLOWED_USER_IDS="123456,789012" \
  cheketop
```

---

## Какие файлы нужны для бота

```
bot_standalone.py, receipt_db.py, pdf_patcher.py
vtb_patch_from_config.py, vtb_cmap.py, vtb_sber_reference.py
vtb_test_generator.py, vtb_sbp_layout.py
cid_patch_amount.py (для Альфа)
layout_config.json, layout_overrides.json
база_чеков/vtb/СБП/, база_чеков/vtb/ВТБ на ВТБ/, база_чеков/alfa/
requirements-bot.txt
```
