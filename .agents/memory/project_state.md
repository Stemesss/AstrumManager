---
name: Project state
description: Текущий статус проекта, версия, этап — обновляется после каждого задания
---

# Текущее состояние проекта

## Статус

```
STATUS:   STABLE
VERSION:  1.2.4
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

Исправление генерации Telegram custom_title (v1.2.4 / AUD-007):
- Старый формат «Воин | Ник» полностью удалён.
- Новый формат: `{symbol} {game_nick} — {role_label}` для всех 4 ролей.
- MEMBER теперь тоже получает кастомный титул (◇ {ник} — Участник).
- Источник имени — только game_nick, никогда Telegram username/first_name.
- Исправлены 5 файлов: sync_title.py, nick.py, setrole.py, group_nick.py, members.py.

## База данных

- Файл: `data/astrum.db`
- Движок: SQLite, WAL-режим ✅
- Таблицы: `users` (14), `audit_log` (26), `news` (0), `forum_topics` (9),
  `publication_attachments` (0), `complaints` (0)

## Переменные окружения

- `TELEGRAM_BOT_TOKEN`  — ✅ установлен (Replit Secrets)
- `BOT_OWNER_ID`        — ✅ установлен (shared env var: 8490615925)
- `GITHUB_TOKEN`        — ✅ используется push.sh (найден автоматически)
- `AstrumManagerMain`   — ✅ установлен (fallback для push.sh)
- `WEBHOOK_SECRET`      — генерируется автоматически (не в Secrets — норма)
