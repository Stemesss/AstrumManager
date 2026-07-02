---
name: Project state
description: Текущий статус проекта, версия, этап — обновляется после каждого задания
---

# Текущее состояние проекта

## Статус

```
STATUS:   STABLE
VERSION:  1.0
DATE:     2026-07-02
PLATFORM: Replit
```

## Воркфлоу

| Процесс | Статус | Порт |
|---------|--------|------|
| Telegram Bot (Python / aiogram 3) | RUNNING | 6000 |
| API Server (Node.js / Express) | RUNNING | 8080 |
| Component Preview Server (Vite) | RUNNING | 8081 |

## Этапы

| Этап | Приоритет | Статус |
|------|-----------|--------|
| Этап 1 | Critical | ✅ завершён |
| Этап 2 | High | ✅ завершён |
| Этап 3 | Medium | ✅ завершён |
| Этап 4 | Low | ✅ завершён |

## Последнее задание

Создание scripts/push.sh и scripts/pull.sh; обновление replit.md и PROJECT_HISTORY.md.

## Следующий этап

Новые задачи по указанию пользователя. Все плановые этапы выполнены.

## База данных

- Файл: `data/astrum.db`
- Движок: SQLite, WAL-режим
- Таблицы: `users`, `audit_log`, `news`, `forum_topics`, `publication_attachments`, `complaints`
- Бэкапы: `data/backups/astrum_{timestamp}.db`

## Переменные окружения

- `TELEGRAM_BOT_TOKEN` — ✅ установлен (Replit Secrets)
- `WEBHOOK_BASE_URL` — не установлен (используется `REPLIT_DOMAINS`)
- `WEBHOOK_PORT` — не установлен (default: 6000)
