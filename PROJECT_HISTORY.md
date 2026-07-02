# PROJECT_HISTORY.md — История проекта AstrumManager

Версия: 1.0
Статус: STABLE
Последнее обновление: 2026-07-02

---

## О ПРОЕКТЕ

**AstrumManager** — Telegram-бот для управления игровым кланом.
Построен на Python 3.11 + aiogram 3, работает в webhook-режиме на Replit и Railway.
База данных: SQLite (aiosqlite, WAL-режим).
Прокси: Node.js / Express 5 (порт 8080) → Python-бот (порт 6000).

---

## ЭТАПЫ РАЗРАБОТКИ

### ✅ Этап 1 — Critical (завершён)

**Цель:** Базовая работоспособность бота на Replit.

**Выполнено:**
- Настроен webhook-режим (polling заблокирован на Replit на уровне сети).
- Реализован двухпроцессный дизайн: Node.js прокси + Python aiohttp-сервер.
- Автодетекция публичного хоста: `WEBHOOK_BASE_URL` → `REPLIT_DOMAINS` → `RAILWAY_PUBLIC_DOMAIN` → polling (local).
- Подключена база данных SQLite с WAL-режимом (`data/astrum.db`).
- Созданы базовые таблицы: `users`, `audit_log`, `forum_topics`, `news`, `publication_attachments`, `complaints`.
- Реализованы команды `/start`, `/help`, базовый echo-handler.
- Настроен `LoggingMiddleware` для логирования всех входящих апдейтов.
- Настроена инъекция зависимостей через `dp["service_name"]`.
- Бот запускается, регистрирует вебхук, принимает сообщения.

---

### ✅ Этап 2 — High (завершён)

**Цель:** Основной функционал — ники, роли, пользователи.

**Выполнено:**
- Реализован `UserService` с полным CRUD пользователей.
- Введены роли: `LEADER`, `ELDER`, `CLAN_CHILD`, `MEMBER`.
- Реализована система игровых ников: `/nick` — регистрация, `/setrole` — смена роли.
- `game_nick` хранит только имя; полный ник вычисляется через `build_full_nick(name, role)`.
- Формат полного ника: `{эмодзи} {роль}｜{имя}` (разделитель U+FF5C).
- Реализован `NickGateMiddleware` — блокирует незарегистрированных пользователей.
- Реализована синхронизация заголовка пользователя в Telegram-группе (`sync_title.py`).
- Handler `/setrole` доступен только администраторам.

---

### ✅ Этап 3 — Medium (завершён)

**Цель:** Расширенный функционал — новости, контент, члены клана, аудит.

**Выполнено:**
- Реализован `AuditService`: логирование всех действий пользователей.
- Реализован `NewsService`: создание и публикация новостей в форум-топики.
- Реализован `TopicService`: синхронизация тем форума с Telegram Topics.
- Реализован раздел `/admin` — панель администратора с подменю.
- Реализован раздел **Members** (подменю → список → удаление → сезон).
- Защита удаления: нельзя удалить суперпользователя (8490615925), себя или LEADER.
- Реализованы разделы контента: `/news`, `/publish`, `/content`.
- Реализован раздел `/complaints` — жалобы и предложения.
- Реализован раздел `/rules` — правила клана.
- Реализован раздел `/icons` — управление иконками.

---

### ✅ Этап 4 — Low (завершён)

**Цель:** Полировка — статистика, сброс сезона, стабилизация.

**Выполнено:**
- Реализован `StatsService`: очки вычисляются on-the-fly из `audit_log`.
  Формула: news_create=5, guide_create=10, screenshot_upload=2, event_create=8.
- Реализованы разделы `/stats` и `/statistics` — лидерборды и отчёты.
- Реализован сброс сезона: `DELETE FROM audit_log` с предварительным бэкапом в `data/backups/astrum_{ts}.db`.
- Реализован `/debug` — вспомогательный handler для отладки.
- Реализован `/group` и `/group_nick` — управление групповым чатом.
- Стабилизирован порядок регистрации роутеров в `main.py`:
  `cancel → common → setrole → nick → audit → news → publish → topics → icons → members → content → complaints → rules → admin → stats → statistics → menu → echo`
- Проведены smoke-тесты (ожидаемые ошибки "chat not found" — нормальны для фейковых ID).
- Проект переведён в статус **STABLE**.

---

## МИГРАЦИЯ НА REPLIT (2026-07-02)

- Проект перенесён в новую среду Replit.
- Установлены Python-зависимости: aiogram, aiohttp, aiosqlite, aiofiles, python-dotenv, pydantic, magic-filter.
- Установлены Node.js-зависимости через pnpm.
- Добавлены секреты `TELEGRAM_BOT_TOKEN` и `GITHUB_TOKEN`.
- Все три воркфлоу запущены и стабильны.
- Восстановлена система памяти агента.
- Настроен git push через GITHUB_TOKEN (прямой URL, без изменения remote config).
- Созданы `scripts/push.sh` и `scripts/pull.sh` для управления синхронизацией с GitHub.

---

## ТЕКУЩАЯ ВЕРСИЯ

```
VERSION: 1.0
STATUS: STABLE
DATE: 2026-07-02
```
