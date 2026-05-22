FROM python:3.11-slim

WORKDIR /app

# Зависимости (PyMuPDF для базы чеков)
COPY requirements-bot.txt ./
RUN pip install --no-cache-dir -r requirements-bot.txt 2>/dev/null || true

# Код и данные (база_чеков, layout_config и т.д.)
COPY . ./

ENV TELEGRAM_BOT_TOKEN=""
ENV ALLOWED_USER_IDS=""
ENV HTTPS_PROXY=""
ENV PORT=10000

# run_render: HTTP health-check + бот (для Render, Railway и др.)
# Используйте bot_standalone.py для простого long-polling
CMD ["python3", "run_render.py"]
