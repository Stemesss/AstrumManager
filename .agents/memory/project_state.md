---
name: Project state
description: Текущий статус проекта, версия, этап — обновляется после каждого задания
---

# Текущее состояние проекта

## Статус

```
STATUS:   STABLE
VERSION:  1.3.3
DATE:     2026-07-05
PLATFORM: Replit (аккаунт @Stemessss)
HEAD:     (после push — см. git ls-remote)
GIT SYNC: ожидает push + force reconciliation с remote
```

## Воркфлоу

| Процесс | Статус | Порт |
|---------|--------|------|
| Telegram Bot (Python / aiogram 3) | RUNNING | 6000 |
| API Server (Node.js / Express) | RUNNING (PID-стабильный) | 8081 |
| artifacts/api-server — дубликат | FAILED (port conflict — норма) | — |
| Component Preview Server (Vite) | RUNNING | 8084 |

## Последнее задание

Задание №15 — «Правила, обращения, Центр статистики» (v1.3.2):
- ✅ rules.py: правило 7 → «2 дней», правило 8 → «Детей клана и Старейшин»
- ✅ complaints.py: рассылка уведомлений Лидеру + Дитя клана + Старейшинам при создании обращения
- ✅ keyboards/statistics.py: меню сокращено до 4 кнопок (Активный, Топ-10, Рост, Закрыть)
- ✅ py_compile OK; assert-проверки меню и правил прошли; workflow RUNNING

Предыдущий завершённый этап: Задание №13 «Финальный аудит Telethon».
- ✅ main.py: порядок роутеров исправлен — group_nick ПЕРЕД group (catch-all не перехватывает +Nick/!ник)
- ✅ statistics.py: cb_hall_of_fame → Telethon-first фильтрация month_w/week_w через _is_active
- ✅ statistics.py: _fmt_top10_card → формула дополнена «💬 Текст = 1  🖼 Медиа = 2»
- ✅ py_compile 7 файлов OK; порядок роутеров подтверждён assert; workflow RUNNING

Предыдущий завершённый этап: Задание №12 «Очки активности + Telethon + Season-отчёт».
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
