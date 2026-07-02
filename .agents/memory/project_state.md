---
name: Project state
description: Текущий статус проекта, версия, этап — обновляется после каждого задания
---

# Текущее состояние проекта

## Статус

```
STATUS:   STABLE
VERSION:  1.2.2
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

Инициализация проекта после переноса на новый аккаунт Replit.
Полное чтение проекта, всех файлов памяти, проверка Git, workflow, secrets, БД.
Выявлено: GITHUB_TOKEN отсутствует в Secrets (есть AstrumManagerMain — назначение неясно).
Скрипт scripts/push.sh требует именно GITHUB_TOKEN — push в GitHub в текущем состоянии невозможен.

## База данных

- Файл: `data/astrum.db`
- Движок: SQLite, WAL-режим ✅
- Таблицы: `users` (14 строк), `audit_log` (26), `news` (0), `forum_topics` (9),
  `publication_attachments` (0), `complaints` (0), `sqlite_sequence` (3)
- Бэкапов нет (`data/backups/` не создана)

## Переменные окружения

- `TELEGRAM_BOT_TOKEN` — ✅ установлен (Replit Secrets)
- `BOT_OWNER_ID`       — ✅ установлен (shared env var: 8490615925)
- `WEBHOOK_SECRET`     — генерируется автоматически (не в Secrets — норма)
- `GITHUB_TOKEN`       — ❌ ОТСУТСТВУЕТ (push.sh не сможет выполнить push)
- `AstrumManagerMain`  — ✅ присутствует в Secrets (назначение не установлено)
