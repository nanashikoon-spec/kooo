#!/bin/bash
# Запуск тест-бота (читает .env.test вместо .env)
BOT_ENV_FILE="$(dirname "$0")/.env.test" python3 "$(dirname "$0")/bot_standalone.py"
