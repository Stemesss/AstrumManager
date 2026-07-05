---
name: Project state
description: Текущий статус проекта, версия, этап — обновляется после каждого задания
---

# Текущее состояние проекта

## Статус

```
STATUS:   STABLE
VERSION:  1.3.7
DATE:     2026-07-05
PLATFORM: Replit (аккаунт @Stemessss)
HEAD:     a4157a9 (Checkpoint создан, push НЕ выполнен — ожидает следующего цикла)
GIT SYNC: НЕ синхронизирован (push ожидает Checkpoint/следующей итерации)
```

## Воркфлоу

| Процесс | Статус | Порт |
|---------|--------|------|
| Telegram Bot (Python / aiogram 3) | RUNNING | 6000 |
| API Server (Node.js / Express) | RUNNING (PID-стабильный) | 8081 |
| artifacts/api-server — дубликат | FAILED (port conflict — норма) | — |
| Component Preview Server (Vite) | RUNNING | 8084 |

## Последнее задание

Задание №20 — «Подсистема «📣 Рассылки»: этапы 6–9» (v1.3.7):
- ✅ Этап 6: исправлена «❌ Отмена» — `reset_to_main_menu()` гарантированно снимает
  ReplyKeyboard перед показом главного меню; нажатие «Отмена» вне FSM больше не выдаёт
  «Я не понял сообщение»; все выходы из мастера рассылок (успех/ошибка/отмена/закрытие)
  переведены на этот хелпер
- ✅ Этап 7: история рассылок — хаб «📣 Рассылки» → «📊 История» (дата, автор, аудитория,
  статус, текст, sent/failed)
- ✅ Этап 8: шаблоны рассылок — новая таблица `broadcast_templates`, сохранение/список/
  использование/удаление шаблона
- ✅ Этап 9: планировщик отложенной отправки — `broadcasts.scheduled_at`, фоновый
  asyncio-цикл `broadcast_scheduler.py` (проверка раз в 30с), UI планирования и отмены
- ✅ Вход в раздел реструктурирован в хаб-меню (Новая рассылка / Шаблоны / История /
  Запланированные / Закрыть)
- ✅ py_compile всех изменённых/новых файлов — OK; Telegram Bot и API Server — RUNNING;
  вебхук зарегистрирован без ошибок; `main.build_dispatcher()` собирается без исключений
  (программный smoke-test); конфликтов callback_data между модулями не найдено
- ⛔ Ручное тестирование через реальные сообщения в Telegram в рамках этого блока не
  проводилось (только статическая проверка и запуск бота) — рекомендуется точечная проверка
- ⏳ Checkpoint создан платформой автоматически; push в GitHub выполняется в следующей
  итерации (см. `.agents/memory/git-ops.md`)

Задание №19 — «Финальная проверка и повторная отправка объявления» (v1.3.6):
- ✅ Полная контрольная проверка после Задания №18: Telegram Bot RUNNING, webhook на
  `/tg/webhook` (pending_update_count=0), py_compile OK, Telethon подключается,
  `/start` и `/start update` отвечают корректно, главное меню открывается, ошибок в логах нет
- ✅ Изменений кода не потребовалось — все проверки прошли на инфраструктуре, исправленной в 1.3.5
- ✅ Объявление повторно сформировано и отправлено только администратору (id 8490615925) через
  `send_update_announcement()` — username через `bot.get_me()`, без хардкода
- ✅ Инлайн-кнопка «🚀 Обновить AstrumManager» открывает @AstrumManager_bot, deep-link
  `?start=update` передаётся и обрабатывается корректно, reply-клавиатура отсутствует, зависших
  FSM-состояний не обнаружено
- ✅ Checkpoint (63ab1cb) создан автоматически, push выполнен, origin/main синхронизирован

Задание №18 — «Диагностика /start — bot не отвечал» (v1.3.5):
- ✅ Код обработчика `/start` (CommandStart, роутеры, middleware, порядок подключения) —
  проверен полностью, дефектов не найдено
- ✅ Найдена реальная причина: Replit резервирует префикс `/api` на dev-домене для внутренних
  нужд edge-прокси — любой запрос на `<repl>.replit.dev/api/*` получает 502 ДО приложения
- ✅ Вебхук перенесён с `/api/telegram/webhook` на `/tg/webhook` (main.py, telegram.ts, app.ts,
  routes/index.ts)
- ✅ Реальное тестирование через Telethon-аккаунт администратора: `/start` и `/start update`
  теперь получают корректный ответ бота (до исправления — не получали ответа вообще)
- ✅ py_compile OK; `pnpm run build` — OK; Telegram Bot и API Server — RUNNING; вебхук
  зарегистрирован (`getWebhookInfo`: pending_update_count=0, ошибок нет)

Предыдущее завершённое задание: Задание №17 — «Динамический deep-link + очистка ReplyKeyboard» (v1.3.4):
- ✅ Ссылка на бота в inline-кнопке теперь строится динамически через `bot.get_me()`, а не
  захардкожена — реальный username оказался `AstrumManager_bot` (в задании №18 ошибочно был
  зашит `AstrumManagerBot`)
- ✅ `send_update_announcement` при передаче `state` завершает FSM и снимает зависшую
  ReplyKeyboard («❌ Отмена» и т.п.) без видимого следа перед отправкой анонса
- ✅ Тестовый анонс повторно отправлен и доставлен в личный чат администратора
- ✅ py_compile OK; Telegram Bot и API Server — RUNNING; вебхук зарегистрирован
- ⛔ В клановую группу ничего не отправлялось

Предыдущее завершённое задание: Задание №18 — «send_update_announcement — тестовая рассылка админу» (v1.3.3):
- ✅ Проверено окружение: секреты на месте, TELETHON_SESSION подключается (id 8490615925, @Stemessss)
- ✅ Установлены отсутствовавшие зависимости (Python: aiogram/aiohttp/aiosqlite/pydantic/telethon;
  Node: pnpm install) — среда была свежей, workflow падали из-за отсутствия node_modules/.venv
- ✅ `bot/services/announcements.py`: `send_update_announcement(bot, chat_id)` — одна inline-кнопка
  (url, без голых ссылок в тексте)
- ✅ `bot/keyboards/announcement.py`, `bot/handlers/announce_test.py` (временный `/testannounce`,
  доступ только суперпользователю/owner_id)
- ✅ Тестовый анонс реально отправлен и доставлен в личный чат администратора (id 8490615925)
- ✅ py_compile всего проекта OK; Telegram Bot и API Server — RUNNING; вебхук зарегистрирован
- ⛔ В клановую группу ничего не отправлялось (по требованию задания — только TEST режим)

Предыдущее завершённое задание: Задание №15 — «Правила, обращения, Центр статистики» (v1.3.2):
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
