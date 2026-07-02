---
name: Change log
description: Журнал изменений — обновляется после каждого выполненного задания
---

# Журнал изменений

## [1.0.1] — 2026-07-02 — Git-скрипты

### Добавлено
- `scripts/push.sh` — push в GitHub через GITHUB_TOKEN; показывает список коммитов и результат
- `scripts/pull.sh` — информирует о состоянии и объясняет ограничение pull в среде Replit

### Изменено
- `replit.md` — добавлен раздел "Git Scripts"
- `PROJECT_HISTORY.md` — добавлена запись о git-скриптах и GITHUB_TOKEN

### Замечания
- git pull/fetch заблокированы платформой Replit (пишут в .git/objects/)
- git push работает штатно через прямой URL с токеном
- pull.sh выводит инструкцию для ручного запуска из Shell

---

## [1.0] — 2026-07-02 — Миграция и восстановление памяти

### Добавлено
- Установлены Python-зависимости: aiogram==3.7.0, aiohttp==3.9.5, aiosqlite==0.20.0, aiofiles==23.2.1, python-dotenv==1.2.2, pydantic==2.7.4, magic-filter==1.0.12
- Установлены Node.js-зависимости через pnpm install
- Добавлен секрет `TELEGRAM_BOT_TOKEN` в Replit Secrets
- Созданы файлы системы памяти агента:
  - `AGENT_START.md`
  - `PROJECT_HISTORY.md`
  - `.agents/memory/project_state.md`
  - `.agents/memory/change_log.md`
  - `.agents/memory/audit.md`
  - `.agents/memory/workflow.md`
  - `.agents/memory/dev_rules.md`
- Обновлён `replit.md` (версия, статус, ссылка на AGENT_START.md)
- Обновлён `.agents/memory/MEMORY.md` (добавлены ссылки на новые файлы)

### Исправлено
- Восстановлен запуск всех трёх воркфлоу после миграции на Replit

### Статус
- VERSION: 1.0
- STATUS: STABLE

---

## [0.4] — до миграции — Этап 4 (Low)

### Добавлено
- StatsService: очки on-the-fly из audit_log
- Разделы /stats и /statistics (лидерборды, отчёты)
- Сброс сезона с бэкапом БД
- Handlers: /debug, /group, /group_nick
- Стабилизирован порядок роутеров в main.py

---

## [0.3] — до миграции — Этап 3 (Medium)

### Добавлено
- AuditService, NewsService, TopicService
- Панель администратора /admin с подменю
- Members: список, удаление, защита суперпользователя
- /news, /publish, /content, /complaints, /rules, /icons

---

## [0.2] — до миграции — Этап 2 (High)

### Добавлено
- UserService (CRUD пользователей)
- Роли: LEADER, ELDER, CLAN_CHILD, MEMBER
- Система ников: /nick, /setrole, build_full_nick()
- NickGateMiddleware
- sync_title.py

---

## [0.1] — до миграции — Этап 1 (Critical)

### Добавлено
- Webhook-режим, двухпроцессный дизайн (Node.js + Python)
- Автодетекция хоста (WEBHOOK_BASE_URL / REPLIT_DOMAINS / RAILWAY_PUBLIC_DOMAIN)
- SQLite + WAL, базовые таблицы
- /start, /help, echo-handler, LoggingMiddleware
- Инъекция зависимостей через dp["service_name"]
