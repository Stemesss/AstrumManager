---
name: Project state
description: Текущий статус проекта, версия, этап — обновляется после каждого задания
---

# Текущее состояние проекта

## Статус

```
STATUS:   STABLE
VERSION:  1.2.1
DATE:     2026-07-02
PLATFORM: Replit
```

## Воркфлоу

| Процесс | Статус | Порт |
|---------|--------|------|
| Telegram Bot (Python / aiogram 3) | RUNNING | 6000 |
| API Server (Node.js / Express) | RUNNING | 8080 |
| Component Preview Server (Vite) | RUNNING | 8081 |

## Последнее задание

Финальная полировка проекта (полный аудит): найден и исправлен критический
дефект AUD-004 (бот не запускался — AttributeError: BTN.GUIDES), очищены
неиспользуемые импорты и мёртвые f-строки, устранено дублирование констант
и зависимостей (AUD-005, AUD-006). Все три воркфлоу перезапущены и работают.

## База данных

- Файл: `data/astrum.db`
- Движок: SQLite, WAL-режим
- Таблицы: `users`, `audit_log`, `news`, `forum_topics`, `publication_attachments`, `complaints`

## Переменные окружения

- `TELEGRAM_BOT_TOKEN` — ✅ установлен (Replit Secrets)
- `WEBHOOK_SECRET` — ✅ установлен или auto-generated
- `GITHUB_TOKEN` — ✅ установлен (для git push)
