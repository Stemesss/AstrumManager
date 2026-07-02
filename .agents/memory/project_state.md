---
name: Project state
description: Текущий статус проекта, версия, этап — обновляется после каждого задания
---

# Текущее состояние проекта

## Статус

```
STATUS:   STABLE
VERSION:  1.2.3
DATE:     2026-07-02
PLATFORM: Replit (новый аккаунт, перенос 2026-07-02)
```

## Воркфлоу

| Процесс | Статус | Порт |
|---------|--------|------|
| Telegram Bot (Python / aiogram 3) | RUNNING | 6000 |
| API Server (Node.js / Express) | RUNNING | 8080 |
| Component Preview Server (Vite) | RUNNING | 8081 |

## Последнее задание

Финальная настройка окружения (v1.2.3):
- scripts/push.sh — поддержка GITHUB_TOKEN и AstrumManagerMain (автоматический fallback)
- AGENT_START.md — обязательный цикл сохранения (10 шагов) + новый формат отчёта
- replit.md, dev_rules.md, workflow.md — закреплены постоянные правила цикла сохранения

## База данных

- Файл: `data/astrum.db`
- Движок: SQLite, WAL-режим ✅
- Таблицы: `users` (14), `audit_log` (26), `news` (0), `forum_topics` (9),
  `publication_attachments` (0), `complaints` (0)

## Переменные окружения

- `TELEGRAM_BOT_TOKEN`  — ✅ установлен (Replit Secrets)
- `BOT_OWNER_ID`        — ✅ установлен (shared env var: 8490615925)
- `AstrumManagerMain`   — ✅ установлен (используется как GitHub PAT в push.sh)
- `WEBHOOK_SECRET`      — генерируется автоматически (не в Secrets — норма)
- `GITHUB_TOKEN`        — не требуется (push.sh использует AstrumManagerMain как fallback)
