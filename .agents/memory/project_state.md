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

Задание №1 — «Обновление интерфейса основных разделов» (только UI, без изменения логики):
- ✅ Раздел «Правила» — переоформлен default-текст с тематическими эмодзи по пунктам.
- ✅ Раздел «Администрация» — кнопки «Гайды»/«Скриншоты» убраны из панели (форумные темы
  продолжают работать, AdminBtn-константы и handlers не тронуты).
- ✅ Главное меню — «❓ Помощь» заменено на «📖 Справочник» (BTN.HELP → BTN.HANDBOOK).
- ✅ Новый раздел «📖 Справочник» — заменяет старый «Помощь», версия отображается
  автоматически.
- py_compile OK, workflow Telegram Bot перезапущен без ошибок.
- push: ожидает Replit Checkpoint.

Предыдущий завершённый этап: 2.3 «Полный центр управления участником» (подэтапы 2.3.1–2.3.6).
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
