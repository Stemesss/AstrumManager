---
name: Project state
description: Текущий статус проекта, версия, этап — обновляется после каждого задания
---

# Текущее состояние проекта

## Статус

```
STATUS:   STABLE
VERSION:  1.1
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
| Полировка участников | Low | ✅ завершён |

## Последнее задание

Финальная полировка раздела «Участники»: новый порядок ролей, иконки 👑🛡⭐👤, убрана ⚙️-кнопка, фильтр по game_nick.

## Следующий этап

Новые задачи по указанию пользователя. Все плановые этапы выполнены.

## База данных

- Файл: `data/astrum.db`
- Движок: SQLite, WAL-режим
- Таблицы: `users`, `audit_log`, `news`, `forum_topics`, `publication_attachments`, `complaints`
- Бэкапы: `data/backups/astrum_{timestamp}.db`

## Переменные окружения

- `TELEGRAM_BOT_TOKEN` — ✅ установлен (Replit Secrets)
- `WEBHOOK_SECRET` — ✅ установлен (Replit Secrets) или auto-generated
- `WEBHOOK_BASE_URL` — не установлен (используется `REPLIT_DOMAINS`)
- `WEBHOOK_PORT` — не установлен (default: 6000)
