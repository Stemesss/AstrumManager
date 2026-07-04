---
name: Project state
description: Текущий статус проекта, версия, этап — обновляется после каждого задания
---

# Текущее состояние проекта

## Статус

```
STATUS:   STABLE
VERSION:  1.2.9
DATE:     2026-07-04
PLATFORM: Replit (аккаунт @Stemessss)
HEAD:     (после push — см. git ls-remote)
GIT SYNC: ожидает push
```

## Воркфлоу

| Процесс | Статус | Порт |
|---------|--------|------|
| Telegram Bot (Python / aiogram 3) | RUNNING | 6000 |
| API Server (Node.js / Express) | RUNNING (PID-стабильный) | 8081 |
| artifacts/api-server — дубликат | FAILED (port conflict — норма) | — |
| Component Preview Server (Vite) | RUNNING | 8084 |

## Последнее задание

Задание №5 — «Telethon MTProto как основной источник синхронизации участников»:
- ✅ cancel.py — NickChange-специфичный обработчик отмены (возврат в профиль).
- ✅ nick.py — CANCEL_KB в промптах NickChange; _CHANGE_PREVIEW_KB с кнопкой
  «❌ Отмена»; cb_nick_cancel_change (state=NickChange.waiting_confirm).
- ✅ members.py — _is_test_user() фильтр; _view_list_users() принимает bot/group_chat_id
  и фильтрует (Test)/(T) + отсутствующих в группе; del_list не тронут.
- Проверено: py_compile 3 файлов OK; workflow RUNNING; HTTP 200 в логах.

Предыдущий завершённый этап: Задание №1 «Обновление интерфейса основных разделов».
См. `.agents/memory/change_log.md` для полной истории.

## База данных

- Файл: `data/astrum.db`
- Движок: SQLite, WAL-режим ✅
- Таблицы: `users` (14), `audit_log` (26+), `news` (0), `forum_topics` (9),
  `publication_attachments` (0), `complaints` (0)

## Переменные окружения

- `TELEGRAM_BOT_TOKEN`  — ✅ установлен (Replit Secrets)
- `BOT_OWNER_ID`        — ✅ установлен (shared env var: 8490615925)
- `GITHUB_TOKEN`        — ✅ используется push.sh (найден автоматически)
- `AstrumManagerMain`   — ✅ установлен (fallback для push.sh)
- `WEBHOOK_SECRET`      — генерируется автоматически (не в Secrets — норма)
