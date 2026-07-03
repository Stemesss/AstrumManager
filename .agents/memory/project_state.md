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

Подэтап 2.3.1 — смена игрового ника участника прямо из карточки (админ-действие):
- `member_card_kb()` — добавлена кнопка «✏️ Ник», кнопка роли переименована в «⭐ Роль»
  (сама функция смены роли не менялась, работает с v1.2.8).
- Новый FSM `MemberNickEdit.waiting_name` (bot/states/members.py).
- `cb_mem_nick_start` → `fsm_mem_nick_enter` (bot/handlers/members.py): валидация через
  `validate_name`, сохранение `user_service.set_game_nick`, синхронизация Telegram
  custom_title через `sync_admin_title`, запись в audit_log (`MEMBER_NICK_CHANGE`),
  показ обновлённой карточки через существующую `member_card_kb` — новых карточек/меню нет.

Следующие подэтапы (2.3.2–2.3.7): target_id в audit_log + таблицы warnings/admin_notes,
предупреждения, заметки администрации, история участника, финальная сверка прав доступа.
См. `.agents/memory/change_log.md` для истории Этапа 2.2 и более ранних этапов.

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
