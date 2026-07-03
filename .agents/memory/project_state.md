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
HEAD:     26de1fe
GIT SYNC: origin/main == local HEAD (26de1fe) — подтверждено git ls-remote
```

## Воркфлоу

| Процесс | Статус | Порт |
|---------|--------|------|
| Telegram Bot (Python / aiogram 3) | RUNNING | 6000 |
| API Server (Node.js / Express) | RUNNING | 8080 |
| Component Preview Server (Vite) | RUNNING | 8081 |

## Последнее задание

Этап 2.2 — редизайн раздела «Участники» (только интерфейс, без изменений логики/ролей/API):
- `_card_text()` (bot/handlers/members.py) — единая карточка для админ-режима и режима просмотра,
  теперь принимает `stats_service` и показывает очки активности (`user_activity`) и
  Telegram-титул (`build_admin_title`); блоки визуально разделены линиями ━━━.
- `members_menu_kb()` — кнопки сгруппированы попарно по смыслу (Отчёт+Очистить,
  Синхронизация+Новый сезон); кнопки «⚙ Настройки» в разделе нет (как и требовалось).
- `member_card_kb()` — «Роль» и «Статистика» объединены в одну строку.
- callback_data и бизнес-логика не менялись; см. `.agents/memory/change_log.md` для истории
  предыдущих этапов (welcome flow, роли, синхронизация тайтлов).

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
