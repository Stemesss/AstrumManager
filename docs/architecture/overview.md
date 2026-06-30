# Обзор системы

## 1. Основная структура репозитория

Проект совмещает два runtime-направления:

1. **Основной продукт** — Telegram-бот на Python/aiogram.
2. **Вспомогательная TypeScript workspace** — API-прокси, OpenAPI-артефакты, заготовки для будущих сервисов и sandbox UI.

Ключевые каталоги:

- `main.py` — главная точка входа Python-бота.
- `bot/` — конфигурация, БД, сервисы, хендлеры, модели, middleware, FSM-состояния, клавиатуры и утилиты.
- `artifacts/api-server/` — Express-сервер, который проксирует Telegram webhook в Python-процесс.
- `artifacts/mockup-sandbox/` — отдельный UI sandbox, не участвующий в бизнес-логике бота.
- `lib/api-spec/` — OpenAPI-спецификация.
- `lib/api-zod/`, `lib/api-client-react/` — сгенерированные API-артефакты.
- `lib/db/` — заготовка PostgreSQL/Drizzle слоя, пока не используемая ботом.
- `data/astrum.db` — локальная SQLite-база по умолчанию.

## 2. Точки входа

### 2.1 Python-бот

Основная точка входа: `main.py`.

Последовательность запуска:

1. `load_config()`
2. `setup_logging(level_name)`
3. создание `Bot`
4. создание `Database`
5. `build_dispatcher(db, config, owner_id, group_chat_id, metrics)`
6. выбор runtime:
   - `run_webhook(...)`, если найден публичный хост;
   - `run_polling(...)`, если публичный хост отсутствует.

Webhook path централизован в `config.runtime.webhook_path`: по умолчанию это `/api/telegram/webhook`, но значение можно переопределить через `WEBHOOK_PATH`.

### 2.2 Node.js proxy

Вспомогательная точка входа: `artifacts/api-server/src/index.ts`.

Express-приложение:

- читает обязательный `PORT`;
- поднимает приложение из `src/app.ts`;
- отдаёт `/api/healthz`;
- проксирует `/api/telegram/*` на Python-бота через `http://localhost:${PYTHON_BOT_PORT}`.

## 3. Runtime-режимы Python-бота

### 3.1 Webhook mode

Выбирается, если в `config.runtime.public_host` найден публичный хост, собранный из одного из источников:

1. `WEBHOOK_BASE_URL`
2. `REPLIT_DOMAINS`
3. `RAILWAY_PUBLIC_DOMAIN`

При старте:

- открывается SQLite;
- выполняется посев тем `seed_default_topics()`;
- запускается стартовая проверка тем;
- бот регистрирует webhook через Telegram Bot API;
- `aiohttp` слушает порт `PORT` или `WEBHOOK_PORT`, по умолчанию `6000`.

### 3.2 Polling mode

Используется как fallback для локального запуска, если публичный хост не найден.

При старте:

- открывается SQLite;
- выполняется посев и проверка тем;
- запускается `dp.start_polling(...)`.

## 4. Конфигурация окружения

### Обязательная для Python-бота

- `TELEGRAM_BOT_TOKEN`

### Необязательная для Python-бота

- `DB_PATH` — путь к SQLite, по умолчанию `data/astrum.db`
- `BOT_OWNER_ID`
- `GROUP_CHAT_ID`
- `LOG_LEVEL`
- `WEBHOOK_BASE_URL`
- `REPLIT_DOMAINS`
- `RAILWAY_PUBLIC_DOMAIN`
- `WEBHOOK_PATH`
- `WEBHOOK_PORT`
- `PORT`
- `FEATURE_OBSERVABILITY`
- `FEATURE_HEALTHCHECK`
- `FEATURE_METRICS`
- `OBSERVABILITY_HOST`
- `OBSERVABILITY_PORT`
- `OBSERVABILITY_PATH_PREFIX`

### Для Node.js proxy

- `PORT` — обязателен
- `PYTHON_BOT_PORT` — по умолчанию `6000`

## 5. Наблюдаемый deployment-контур

- `Procfile` запускает `python3 main.py`.
- `nixpacks.toml` устанавливает Python-зависимости из `requirements.txt` и тоже запускает `python3 main.py`.
- Node.js proxy является отдельным runtime-компонентом и нужен в окружениях, где Telegram webhook должен приходить через внешний HTTP-процесс.
