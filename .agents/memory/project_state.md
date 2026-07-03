---
name: Project state
description: Текущий статус проекта, версия, этап — обновляется после каждого задания
---

# Текущее состояние проекта

## Статус

```
STATUS:   STABLE
VERSION:  1.2.8
DATE:     2026-07-03
PLATFORM: Replit (новый аккаунт, перенос 2026-07-02)
HEAD:     e500502
GIT SYNC: origin/main == local HEAD (e500502) — подтверждено git ls-remote
```

## Воркфлоу

| Процесс | Статус | Порт |
|---------|--------|------|
| Telegram Bot (Python / aiogram 3) | RUNNING | 6000 |
| API Server (Node.js / Express) | RUNNING | 8080 |
| Component Preview Server (Vite) | RUNNING | 8081 |

## Последнее задание

Этап 2.3 — «Полный центр управления участником» (план из 7 подэтапов подтверждён
пользователем; архитектурное решение: отдельного поля custom_title в БД нет и не будет —
title всегда = символ_роли + game_nick; для точной истории участника согласовано добавление
target_id в audit_log — реализуется в подэтапе 2.3.2).

Подэтапы 2.3.1–2.3.6 завершены:
- 2.3.1 ✅ смена ника участника из карточки
- 2.3.2 ✅ target_id в audit_service.log() для смены роли, ника, удаления
- 2.3.3 ✅ UI предупреждений: warnings_kb, MemberWarnAdd FSM, 4 handlers
- 2.3.4 ✅ UI заметок: notes_kb, MemberNoteAdd FSM, 4 handlers
- 2.3.5 ✅ История участника: cb_mem_history, get_user_history(uid, limit=20)
- 2.3.6 ✅ Финальная сверка прав: все handlers через _check_admin(); суперпользователь
          защищён от предупреждений; cancel handler покрывает все FSM.

Этап 2.3 «Полный центр управления участником» — ЗАВЕРШЁН.
Следующий этап: 2.4 или по заданию пользователя.
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
