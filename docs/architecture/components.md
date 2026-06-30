# Компоненты и зависимости

## 1. Python-бот (`bot/`)

### 1.1 Конфигурация

- `bot/config/settings.py` — dataclass `Config` и `load_config()`.
- `bot/config/__init__.py` — совместимый публичный re-export `Config`, `load_config`.

### 1.2 База данных

- `bot/database/db.py` — единственный активный слой доступа к данным.
- Текущая БД: SQLite через `aiosqlite`.

Таблицы, создаваемые при `connect()`:

- `users`
- `news`
- `audit_log`
- `forum_topics`
- `publication_attachments`
- `complaints`

Внутри `connect()` также встроены прикладные миграции через `ALTER TABLE`:

- `users.game_nick`
- `news.content_type`
- `forum_topics.icon_custom_emoji_id`

### 1.3 Сервисы

Сервисы создаются в `main.py` и получают `Database` через конструктор:

- `UserService`
- `NewsService`
- `AuditService`
- `StatsService`
- `TopicService`

Назначение сервисов:

- `UserService` — регистрация, роли, ники, профиль, сезонный сброс и удаление участников.
- `NewsService` — CRUD для контента на базе таблицы `news`.
- `AuditService` — запись и чтение журнала действий.
- `StatsService` — агрегированная статистика по пользователям и контенту.
- `TopicService` — единая точка управления форумными темами, публикацией и иконками.

### 1.4 Middleware

- `bot/middlewares/logging.py` — глобальный logging middleware для входящих update.
- `bot/middlewares/nick_gate.py` — приватный gate, который ограничивает доступ пользователям без игрового ника.

### 1.5 FSM-состояния

Состояния расположены в `bot/states/`:

- `nick.py`
- `news.py`
- `audit.py`
- `complaints.py`
- `members.py`
- `topics.py`
- `content.py`
- `rules.py`
- `publish.py`

Они поддерживают многошаговые диалоги в приватном интерфейсе бота.

### 1.6 Хендлеры

#### Групповые роутеры

- `bot/handlers/group.py`
- `bot/handlers/group_nick.py`

Назначение:

- ограниченная логика в группе/супергруппе;
- приветствие новых участников;
- group-specific обработка ника и связанных действий;
- перенаправление пользователя в личный чат.

#### Приватные роутеры

- `cancel.py`
- `common.py`
- `setrole.py`
- `nick.py`
- `audit.py`
- `news.py`
- `publish.py`
- `topics.py`
- `icons.py`
- `members.py`
- `content.py`
- `complaints.py`
- `rules.py`
- `admin.py`
- `stats.py`
- `statistics.py`
- `menu.py`
- `echo.py`

#### Отдельный временный роутер

- `debug.py`

Он подключается глобально до разделения на private/group и задуман как временный отладочный слой.

### 1.7 Модели

В `bot/models/` определены:

- `user.py` — `User`, `UserRole`
- `news.py` — `NewsItem`
- `audit.py` — `AuditAction`, `CATEGORY_ACTIONS`, `CATEGORY_LABELS`
- `stats.py` — `UserActivity`, `AuthorStat`, `NewsStats`, `ContentStats`, `ClanGrowth`
- `topic.py` — `TopicDefinition`, `ForumTopic`, `TOPIC_REGISTRY`, `DEFAULT_THREAD_IDS`

### 1.8 UI-слой Telegram

- `bot/keyboards/` — reply и inline keyboards.
- `bot/utils/` — форматирование ника, текста, ролей, профиля, синхронизация заголовков.

## 2. Главный composition root

`build_dispatcher()` в `main.py` — главный слой композиции приложения.

Он:

- создаёт Dispatcher;
- инжектит сервисы и shared values в `dp[...]`;
- подключает middleware;
- собирает порядок роутеров;
- отделяет group flow от private flow.

Инжектируемые значения:

- `dp["user_service"]`
- `dp["news_service"]`
- `dp["audit_service"]`
- `dp["stats_service"]`
- `dp["topic_service"]`
- `dp["group_chat_id"]`
- `dp["db"]`
- `dp["owner_id"]`

Во время startup добавляется ещё:

- `dp["bot_start_time"]`
- `dp["bot_username"]`

## 3. TypeScript workspace

### 3.1 Root workspace

`package.json` на корне задаёт:

- `pnpm run build`
- `pnpm run typecheck`
- `pnpm run typecheck:libs`

Workspace используется как вспомогательный слой и не заменяет Python-бота.

### 3.2 API proxy (`artifacts/api-server`)

Реальные runtime-компоненты:

- `src/index.ts`
- `src/app.ts`
- `src/routes/index.ts`
- `src/routes/health.ts`
- `src/routes/telegram.ts`
- `src/lib/logger.ts`

Назначение:

- health endpoint;
- журналирование HTTP-запросов;
- proxy webhook-запросов в Python-процесс;
- безопасный пропуск Telegram request body без `express.json()`.

### 3.3 API spec и сгенерированные библиотеки

- `lib/api-spec/openapi.yaml` — текущий API-контракт health endpoint.
- `lib/api-zod/` — zod-типизация, сгенерированная из OpenAPI.
- `lib/api-client-react/` — клиентские артефакты для React.

### 3.4 `lib/db`

Это пока подготовка к отдельному PostgreSQL/Drizzle слою:

- `drizzle.config.ts` требует `DATABASE_URL`;
- `src/schema/index.ts` пока не содержит продуктивной схемы;
- бот этот пакет не использует.
