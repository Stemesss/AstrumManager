---
name: Change log
description: Журнал изменений — обновляется после каждого выполненного задания
---

# Журнал изменений

## [1.3.7] — 2026-07-05 — Подсистема «📣 Рассылки»: этапы 6–9 (отмена, история, шаблоны, планировщик)

### Этап 6 — исправление «❌ Отмена»
- `bot/keyboards/nav.py` — новый хелпер `reset_to_main_menu(message, text)`: отправляет
  сообщение с `ReplyKeyboardRemove()`, затем отдельным сообщением главное меню — гарантирует,
  что старая Reply-клавиатура не остаётся видимой при любом выходе из FSM.
- `bot/handlers/cancel.py` — `handle_global_cancel` и обработка отмены смены ника используют
  явный `ReplyKeyboardRemove()` перед восстановлением меню; добавлен новый обработчик
  `handle_cancel_outside_fsm` (StateFilter `default_state`) — нажатие «❌ Отмена» вне активного
  сценария больше не показывает «Я не понял сообщение», а просто убирает клавиатуру и
  показывает главное меню.
- `bot/handlers/broadcast.py` — все точки выхода (отмена, отправка себе, отправка всем, закрытие
  хаба, ошибки) переведены на `reset_to_main_menu`; операции отправки обёрнуты в try/except с
  откатом состояния и понятным сообщением об ошибке вместо зависания FSM.

### Этап 7 — история рассылок
- `BroadcastService.list_recent()` (уже был) используется в новом обработчике `cb_history`:
  показывает дату, автора, аудиторию, статус, сокращённый текст, счётчики sent/failed по
  последним 10 рассылкам.

### Этап 8 — шаблоны рассылок
- Новая таблица `broadcast_templates` (id, author_id, author_name, name, text, created_at).
- `Database`: `create/list/get/delete_broadcast_template`. `BroadcastService`: тонкие обёртки
  `save_template/list_templates/get_template/delete_template`.
- Хаб «📣 Рассылки» → «🗂 Шаблоны»: список с использованием (переход сразу в предпросмотр с
  текстом шаблона) и удалением; создание нового шаблона отдельным потоком (текст → название);
  кнопка «💾 Сохранить как шаблон» добавлена прямо в предпросмотр рассылки.
- Новые действия аудита: `BROADCAST_TEMPLATE_SAVE`, `BROADCAST_TEMPLATE_DELETE`.

### Этап 9 — планировщик отложенной отправки
- `broadcasts.scheduled_at TEXT` (миграция ALTER TABLE, автоприменяется при старте).
- `Database`: `schedule_broadcast`, `cancel_scheduled_broadcast`, `list_scheduled_broadcasts`,
  `get_due_scheduled_broadcasts` (сравнение по `datetime('now')`, время хранится в UTC).
- Новый `bot/services/broadcast_scheduler.py`: фоновый asyncio-цикл (проверка раз в 30с),
  запускается в `main.py` (`on_startup`/`on_startup_polling`) как `dp["broadcast_scheduler_task"]`,
  корректно отменяется в `on_shutdown`/`on_shutdown_polling`.
- Предпросмотр рассылки → «⏰ Запланировать»: ввод даты/времени одним сообщением
  (`ДД.ММ.ГГГГ ЧЧ:ММ`, UTC), валидация формата и что время в будущем; всегда аудитория «все
  участники». Хаб → «⏰ Запланированные»: список с кнопкой отмены на каждую запись.
- Новые действия аудита: `BROADCAST_SCHEDULE`, `BROADCAST_SCHEDULE_CANCEL`.

### Реструктуризация входа
- `AdminBtn.BROADCASTS` теперь открывает хаб-меню (✏️ Новая рассылка / 🗂 Шаблоны / 📊 История /
  ⏰ Запланированные / ❌ Закрыть) вместо прямого перехода в мастер создания.

### Проверка
- `python3 -m py_compile` — все изменённые/новые файлы (main.py, bot/handlers/broadcast.py,
  bot/handlers/cancel.py, bot/keyboards/broadcast.py, bot/keyboards/nav.py,
  bot/states/broadcast.py, bot/services/broadcast_service.py,
  bot/services/broadcast_scheduler.py, bot/database/db.py, bot/models/audit.py) — без ошибок.
- Telegram Bot — RUNNING, вебхук зарегистрирован без ошибок; API Server — RUNNING.
- Программный smoke-test: `main.build_dispatcher()` собирается без исключений с новым
  планировщиком и сервисом; проверено отсутствие конфликтов `callback_data` между модулями.
- Ручная проверка через реальные сообщения в Telegram не проводилась в рамках этого блока
  (только статическая проверка кода/старт бота) — рекомендуется точечно протестировать вручную.

---

## [1.3.6] — 2026-07-04 — Задание №19: финальная проверка и повторная отправка объявления

Полная контрольная проверка после исправления вебхука (Задание №18): Telegram Bot RUNNING,
webhook на `/tg/webhook` (pending_update_count=0, ошибок нет), py_compile — без ошибок,
Telethon подключается, `/start` и `/start update` отвечают корректно, главное меню открывается,
ошибок в логах нет. Изменений кода не потребовалось — все проверки прошли успешно на уже
исправленной в 1.3.5 инфраструктуре.

Объявление «🚀 AstrumManager обновлён!» повторно сформировано и отправлено только
администратору (id 8490615925) в личные сообщения через `send_update_announcement()`
(username подтягивается динамически через `bot.get_me()`, без хардкода). Инлайн-кнопка
«🚀 Обновить AstrumManager» ведёт на `https://t.me/AstrumManager_bot?start=update`. Клик по
диплинку смоделирован повторной отправкой `/start update` — бот ответил корректным главным
меню, reply-клавиатура отсутствует, зависших FSM-состояний не обнаружено.

## [1.3.5] — 2026-07-04 — Задание №18: диагностика /start — причина в reserved-префиксе /api на Replit dev-домене

### Причина проблемы
Кнопка «🚀 Обновить AstrumManager» открывала правильного бота (URL был исправлен в 1.3.4), но
бот не отвечал ни на `/start`, ни на `/start update`, ни на обычные сообщения. Полный аудит
кода обработчика `/start` (роутеры, middleware, порядок подключения, `command.args`) не выявил
никаких дефектов — весь код регистрации и обработки `CommandStart()` был корректен.

Причина оказалась инфраструктурной, а не в коде бота: `getWebhookInfo` показал
`last_error_message: "Wrong response from the webhook: 502 Bad Gateway"`. Прямые curl-запросы
на `localhost:8081/api/telegram/webhook` и `localhost:6000/api/telegram/webhook` отрабатывали
штатно (401 — не хватает секрета, это нормально), а те же запросы через публичный dev-домен
`*.replit.dev` возвращали 502 ещё ДО того, как долетали до приложения (в логах Express/aiohttp
запрос не появлялся вовсе). Подтверждено систематически: ЛЮБОЙ путь, начинающийся с `/api`,
на dev-домене отдаёт 502 (зарезервировано платформой Replit для внутренних нужд edge-прокси),
а пути вне `/api` (например `/`) штатно доходят до Express. Именно поэтому вебхук
`/api/telegram/webhook` был недоступен для Telegram, хотя `set_webhook` формально отрабатывал
успешно (сам вызов регистрации не проверяет реальную доступность пути).

### Исправлено (3 файла)
- `main.py`: `WEBHOOK_PATH` изменён с `/api/telegram/webhook` на `/tg/webhook`
- `artifacts/api-server/src/routes/telegram.ts`: прокси теперь слушает префикс `/tg`
  вместо `/api/telegram`
- `artifacts/api-server/src/app.ts`: роутер `telegramRouter` подключён на верхнем уровне
  (вне `/api`), проверка пропуска `express.json()` обновлена на префикс `/tg`
- `artifacts/api-server/src/routes/index.ts`: убран импорт `telegramRouter` (перенесён в app.ts)

### Проверка (реальное тестирование через Telethon-аккаунт администратора)
- До исправления: `/start` и `/start update`, отправленные напрямую в бота через Telethon,
  не получили ответа — подтверждено чтением истории чата (только исходящие сообщения)
- После исправления: `getWebhookInfo` → `pending_update_count: 0`, ошибок нет, URL —
  `.../tg/webhook`; `/start` и `/start update` отправлены повторно через Telethon и
  ПОЛУЧИЛИ корректный ответ бота (приветствие + главное меню)
- py_compile OK (main.py и все изменённые Python-файлы); `pnpm run build` в api-server — OK
- Telegram Bot и API Server — RUNNING; вебхук зарегистрирован и подтверждён рабочим

---

## [1.3.4] — 2026-07-04 — Задание №17: динамический deep-link + очистка ReplyKeyboard

### Изменено (3 файла)
- `bot/keyboards/announcement.py`: статичный `UPDATE_ANNOUNCEMENT_KB`/`UPDATE_BOT_URL` заменены
  на `build_update_announcement_kb(bot_username)` — ссылка строится из реального username бота
- `bot/services/announcements.py`: `send_update_announcement(bot, chat_id, state=None)` теперь
  получает username через `await bot.get_me()` (username менять в коде больше не нужно);
  если передан `state` — вызывает `state.clear()`; перед отправкой анонса снимает любую
  зависшую ReplyKeyboard через служебное сообщение с `ReplyKeyboardRemove()`, которое сразу
  удаляется — у пользователя остаётся только анонс с inline-кнопкой
- `bot/handlers/announce_test.py`: `/testannounce` теперь передаёт `state: FSMContext` в
  `send_update_announcement`

### Проверка
- Реальный username бота подтверждён через `bot.get_me()`: `AstrumManager_bot` (ранее в коде
  ошибочно был захардкожен `AstrumManagerBot`) — теперь ссылка формируется динамически и
  не зависит от смены username в будущем
- Тестовый анонс повторно отправлен и доставлен в личный чат администратора (id 8490615925)
- py_compile OK; Telegram Bot и API Server — RUNNING; вебхук зарегистрирован

---

## [1.3.3] — 2026-07-04 — Задание №18: send_update_announcement (тестовая рассылка админу)

### Добавлено (3 новых файла, 1 изменён)
- `bot/keyboards/announcement.py`: `UPDATE_ANNOUNCEMENT_KB` — InlineKeyboardMarkup с одной
  кнопкой `InlineKeyboardButton(text="🚀 Обновить AstrumManager", url="https://t.me/AstrumManagerBot?start=update")`
- `bot/services/announcements.py`: `send_update_announcement(bot, chat_id)` — универсальная
  функция отправки анонса обновления; текст получен от пользователя (не был в проекте
  заранее, найден только упоминанием в задании — уточнил через вопрос)
- `bot/handlers/announce_test.py`: ВРЕМЕННЫЙ `/testannounce` — доступен только суперпользователю
  (id 8490615925) или `owner_id`; отправляет анонс исполнителю команды в личку (тестовый режим,
  клановая группа не используется)
- `main.py`: зарегистрирован `announce_test.router` в приватном роутере после `admin.router`

### Проверка окружения перед изменениями
- Секреты TELEGRAM_BOT_TOKEN / TELEGRAM_API_ID / TELEGRAM_API_HASH / TELETHON_SESSION — на месте
- Python/Node зависимости отсутствовали в среде (свежий контейнер) — переустановлены
  (aiogram, aiohttp, aiosqlite, pydantic, telethon; pnpm install для monorepo)
- TELETHON_SESSION проверен вручную: подключается без исключений, `get_me()` → id 8490615925 (@Stemessss)
- Тестовое сообщение реально отправлено в личный чат администратора (id 8490615925) — доставлено

### Не затронуто (по требованию задания)
architecture, database, callback_data (существующие), Telethon-логика синхронизации,
роли/права, статистика, activity system, forum topics

---

## [1.3.2p2] — 2026-07-04 — Задание №15: Правила, обращения, Центр статистики

### Изменено (4 файла)
- `bot/handlers/rules.py`: правило 7 — «14 дней» → «2 дней»;
  правило 8 — «Дитя клана» → «Детей клана» (согласовано по падежу)
- `bot/handlers/complaints.py`: `fsm_complaint_content` — добавлена рассылка уведомлений
  при создании обращения: Лидер + Дитя клана + Старейшина (все активные пользователи
  с этими ролями); автор-менеджер пропускается; ошибки отправки логируются в debug
- `bot/keyboards/statistics.py`: STATISTICS_MENU_KB — оставлены только
  🔥 Самый активный, 🏆 Топ-10, 📊 Рост клана, ❌ Закрыть (удалены Новости, События,
  Лучший месяца, Зал славы); callback_data не изменены; handlers не тронуты

---

## [1.3.2p1] — 2026-07-04 — Задание №13: Финальный аудит Telethon и системы активности

### Найдено и устранено (3 файла)
- `main.py`: порядок включения групповых роутеров — group_nick.router был ПОСЛЕ group.router;
  catch-all handler перехватывал +Nick/!ник до group_nick. Исправлено: group_nick ПЕРВЫМ.
- `bot/handlers/statistics.py`: cb_hall_of_fame не фильтровал month_w/week_w по текущему
  членству в группе (непоследовательно с cb_best_month/cb_most_active_week).
  Добавлены bot/group_chat_id/telethon_sync/db параметры; _is_active() вызывается для обоих.
- `bot/handlers/statistics.py`: _fmt_top10_card() — формула не отражала msg_text=+1,
  msg_media=+2. Добавлена строка «💬 Текст = 1  🖼 Медиа = 2».

### Подтверждено без изменений
- members.py cb_mem_clean_absent — Bot API для per-user проверки перед удалением ✅ (норма)
- synctitles.py — Bot API для per-user проверки перед сменой титула ✅ (норма)
- statistics.py _is_active/_filter_active — Telethon-first ✅
- stats.py cb_top1/cb_top10 — Telethon-first ✅
- members.py _view_list_users — Telethon-first ✅
- db.py season_reset — только DELETE FROM audit_log; users/roles/nicks сохранены ✅
- group.py handle_group_message_activity — единственный handler, нет дублирования ✅
- Middleware — LoggingMiddleware (консоль), NickGateMiddleware (только private) ✅

---

## [1.3.2] — 2026-07-04 — Задание №12: Очки активности за сообщения + Telethon + Season-отчёт

### Добавлено / изменено (5 файлов)
- `bot/models/audit.py` — новые константы `MSG_TEXT = "msg_text"` (+1 очко), `MSG_MEDIA = "msg_media"` (+2 очка)
- `bot/database/db.py` — 3 SQL-формулы очков дополнены WHEN для msg_text/msg_media; WHERE IN расширен
- `bot/handlers/group.py` — catch-all handler `handle_group_message_activity`: текст +1, медиа +2; игнорирует ботов, стикеры, сервисные сообщения; только для `group_chat_id`
- `bot/handlers/stats.py` — cb_top1/cb_top10 принимают telethon_sync/db, Telethon-first через sync_and_get_ids; Bot API как fallback
- `bot/handlers/members.py` — season-отчёт в новом формате: 🏆 Новый сезон + 👥 Участников + 📊 Очки обнулены + 📝 Журнал очищен + ✅ Ники сохранены + 🔒 Роли сохранены

### Формула очков (актуальная)
- news_create=5, guide_create=10, screenshot_upload=2, event_create=8, msg_text=1, msg_media=2

---

## [1.3.0] — 2026-07-04 — Задание №9-10: Унификация раздела «Участники» + оформление карточки

### Изменено (только bot/handlers/members.py)
- `_show_list()` — переписана: теперь вызывает `_view_list_users()` внутри (тот же Telethon-first
  источник данных что и главное меню); добавлены параметры telethon_sync, db, group_chat_id, bot.
  Убран `_DIVIDER`, текст: «👤 Всего участников: N».
- `cb_mem_list()` — получает bot, group_chat_id, telethon_sync, db из DI, передаёт в `_show_list`.
- `handle_members_view()` — убран `_DIVIDER`, «Всего:» → «Всего участников:».
- `cb_memv_list()` — убран `_DIVIDER`, «Всего:» → «Всего участников:».
- `_show_delete_list()`, служебные функции (удаление, диагностика, сезон) — БЕЗ ИЗМЕНЕНИЙ.

### Результат
- Главное меню → Участники: Telethon-источник ✅ (было)
- Администрация → Участники: Telethon-источник ✅ (исправлено)
- Оба раздела показывают одинаковое кол-во участников
- Оформление карточки — без `_DIVIDER`, единый стиль

---

## [1.2.9] — 2026-07-04 — Задание №5: Telethon MTProto как основной источник синхронизации участников

### Добавлено (без изменений схемы БД, callback_data и архитектуры)
- `bot/services/telethon_sync.py` — `TelethonSyncService`: ленивая загрузка учётных данных
  из env (TELEGRAM_API_ID / TELEGRAM_API_HASH / TELETHON_SESSION), `fetch_members(group_chat_id)`
  через `iter_participants`, `sync_and_get_ids(group_chat_id, db)` с кэшем 30 сек.,
  upsert-only (ники и роли не трогает), `invalidate_cache()`. При любой ошибке → None (fallback).
- `bot/utils/group_filter.py` — добавлена `filter_by_active_ids(items, get_id, active_ids)`:
  фильтрация без API-вызовов по готовому set[int].
- `bot/handlers/members.py` — `_view_list_users()` принимает `telethon_sync` и `db`;
  сначала пробует Telethon (один MTProto-запрос), при недоступности — Bot API fallback;
  `handle_members_view` и `cb_memv_list` получают `telethon_sync`/`db` из DI.
- `bot/handlers/statistics.py` — добавлены хелперы `_is_active()` и `_filter_active()`;
  `cb_best_month`, `cb_most_active_week`, `cb_top10` принимают `telethon_sync`/`db`,
  используют Telethon-first, Bot API fallback.
- `main.py` — импорт `TelethonSyncService`; создаётся один экземпляр в `build_dispatcher()`,
  инъецируется как `dp["telethon_sync"]`.

### Проверено
- `python3 -m py_compile` — 5 изменённых файлов, без ошибок.
- Workflow «Telegram Bot» — RUNNING, вебхук зарегистрирован, HTTP 200 в логах.
- TelethonSync: ленивая инициализация — при отсутствии секретов логирует предупреждение,
  не падает; при наличии TELETHON_SESSION работает с первого запроса к списку участников.

---

## [1.2.8] — 2026-07-03 — Задание №4: кнопка отмены при смене ника + фильтрация участников

### Изменено (только поведение FSM и отображение списка; callback_data/логика/права/БД не тронуты)
- `bot/handlers/cancel.py` — добавлен NickChange-специфичный обработчик отмены
  (StateFilter NickChange.waiting_name/waiting_confirm); возвращает MAIN_KEYBOARD
  и карточку профиля с PROFILE_KB вместо общего «❌ Действие отменено».
- `bot/handlers/nick.py` — импортирован CANCEL_KB; добавлен _CHANGE_PREVIEW_KB
  (✅ Подтвердить / ✏️ Изменить / ❌ Отмена) для потока NickChange; cb_nick_change_start
  теперь показывает CANCEL_KB при выводе промпта; fsm_change_enter_name показывает
  CANCEL_KB при ошибках и _CHANGE_PREVIEW_KB при предпросмотре; добавлен
  cb_nick_cancel_change (state=NickChange.waiting_confirm) — очищает FSM, восстанавливает
  MAIN_KEYBOARD, показывает профиль.
- `bot/handlers/members.py` — добавлен _is_test_user(); _view_list_users() принимает
  параметры bot/group_chat_id, фильтрует (Test)/(T) по нику и отсутствующих в
  Telegram-группе (fail-open при ошибках API); handle_members_view и cb_memv_list
  передают bot и group_chat_id; _show_delete_list — без изменений (все пользователи).

### Проверено
- `python3 -m py_compile` — 3 изменённых файла, без ошибок.
- Workflow Telegram Bot — RUNNING, вебхук зарегистрирован, HTTP 200.
- Code review: упорядочен FSM state-filter на cb_nick_cancel_change.

## [1.2.8] — 2026-07-03 — Задание №2: единый стиль (Журнал действий / Статистика / Участники)

### Изменено (только UI, callback_data/логика/права/БД/форумные темы не тронуты)
- `bot/keyboards/audit.py` — меню перегруппировано по смыслу (Последние действия,
  Участники, News/Events, Guides/Screenshots 2×2, Поиск/Все записи).
- `bot/handlers/audit.py` — добавлен `_DIVIDER`; разделители встроены в текст меню,
  карточки записей, результаты поиска, подтверждение очистки.
- `bot/keyboards/statistics.py` — `STATISTICS_MENU_KB` перегруппирован (парные кнопки,
  укороченные подписи).
- `bot/handlers/statistics.py` — добавлен `_DIVIDER`; разделители в карточках победителя
  месяца, топ-10, роста клана, зала славы; уточнён текст меню.
- `bot/keyboards/members.py` — добавлен `_member_label(u)` (роль-иконка + ник +
  username/имя, с дедупликацией при совпадении ника и username); применён в
  `members_list_kb`, `delete_list_kb`, `delete_search_result_kb`, `view_list_kb`;
  кнопка «Просмотреть участников» → «Список участников»; разведены дублирующиеся
  иконки 🔄 → 🔁 Синхронизация / 🆕 Новый сезон.
- `bot/handlers/members.py` — добавлен `_DIVIDER`; `_card_text` переработан на
  `role_label()` вместо старого `_ICONS`-бейджа; разделители в меню, списке,
  карточке статистики, подтверждении удаления; подтверждение удаления также
  переведено на `role_label()`.

### Проверено
- `python3 -m py_compile` — 6 изменённых файлов, без ошибок.
- callback_data сверен построчно до/после правок (`grep -o 'callback_data="[^"]*"' | sort`
  по всем 6 файлам) — итоговый diff пустой, 0 отличий.
- Workflow Telegram Bot перезапущен дважды (после блока 3 и после финального фикса
  дедупликации ника/username), оба раза стартовал чисто, вебхук зарегистрирован.
- Runtime smoke-test клавиатур участников через `python3 -c` — обычный участник,
  участник без username, участник с username==nick — рендер меток и клавиатур без ошибок.
- push: ожидает Replit Checkpoint (git commit создаётся платформой автоматически;
  в главном агенте `git commit`/`git add` заблокированы).

## [1.2.8] — 2026-07-03 — Задание №1: обновление интерфейса (Правила / Администрация / Справочник)

### Изменено (только UI, без изменений логики/прав/БД/форумных тем)
- `bot/handlers/rules.py` — `_DEFAULT_RULES_CONTENT` переоформлен с тематическими эмодзи
  по каждому пункту (было — сплошной текст).
- `bot/keyboards/admin_panel.py` — из `ADMIN_PANEL_KB` убраны кнопки «📚 Гайды» и
  «📸 Скриншоты»; `AdminBtn.GUIDES/SCREENSHOTS` и их callback-handlers в `admin.py`
  не тронуты — разделы продолжают работать как форумные темы Telegram.
- `bot/keyboards/main_menu.py` — константа `BTN.HELP` переименована в `BTN.HANDBOOK`
  (текст кнопки: «❓ Помощь» → «📖 Справочник»); проверено, что константа больше нигде
  не используется как ключ конфигурации (в отличие от GUIDES/SCREENSHOTS/MEMES — см.
  `menu-button-coupling.md`), поэтому переименование безопасно.
- `bot/handlers/menu.py` — `handle_help_button` переименован в `handle_handbook_button`,
  фильтр `F.text == BTN.HANDBOOK`, новый текст «📖 Справочник AstrumManager» с описанием
  всех разделов и автоматическим отображением версии (`_APP_VERSION`).

### Проверено
- `python3 -m py_compile` — 4 изменённых файла, без ошибок.
- Workflow Telegram Bot перезапущен, стартовал без ошибок, вебхук зарегистрирован.
- push: ожидает Replit Checkpoint (git commit создаётся платформой автоматически по
  завершении задания; в главном агенте `git commit`/`git add` заблокированы).

## [1.2.8] — 2026-07-03 — Этап 2.3.2–2.3.6: target_id + предупреждения + заметки + история + аудит прав

### Изменено

#### bot/keyboards/members.py
- `MemberBtn`: добавлены статические методы `warnings(uid)`, `warn_add(uid)`, `warn_del(uid, wid)`,
  `notes(uid)`, `note_add(uid)`, `note_del(uid, nid)`, `history(uid)`.
- `member_card_kb()`: добавлены кнопки «⚠️ Предупреждения», «📝 Заметки», «📋 История».
- Новые клавиатуры: `warnings_kb(uid, warn_list)`, `notes_kb(uid, notes_list)`, `history_kb(uid)`.

#### bot/states/members.py
- Добавлены FSM-группы `MemberWarnAdd.waiting_reason` и `MemberNoteAdd.waiting_text`.

#### bot/handlers/members.py
- **2.3.2**: `target_id` передаётся в `audit_service.log()` для смены роли, смены ника, удаления.
- **2.3.3**: Обработчики предупреждений — `cb_mem_warnings`, `cb_mem_warn_add_start`,
  `fsm_mem_warn_reason`, `cb_mem_warn_del`. Защита: суперпользователю нельзя выдать предупреждение.
- **2.3.4**: Обработчики заметок — `cb_mem_notes`, `cb_mem_note_add_start`,
  `fsm_mem_note_text`, `cb_mem_note_del`. AuditAction: MEMBER_NOTE_ADD, MEMBER_NOTE_REMOVE.
- **2.3.5**: Обработчик истории — `cb_mem_history` (audit_log по user_id OR target_id, лимит 20).
- **2.3.6**: Аудит прав — все новые handlers защищены `_check_admin()`;
  Cancel handler покрывает MemberWarnAdd/MemberNoteAdd FSM глобально.

### Проверено
- `python3 -m py_compile` — 3 файла (keyboards/members.py, states/members.py, handlers/members.py), без ошибок.
- push: ожидает Replit Checkpoint.

## [1.2.8] — 2026-07-03 — Этап 2.3.1: смена ника участника из карточки (центр управления)

### Изменено
- `bot/states/members.py` — добавлен `MemberNickEdit.waiting_name`.
- `bot/keyboards/members.py` — `member_card_kb()`: добавлена кнопка «✏️ Ник»
  (`MemberBtn.nick(uid)`), кнопка роли переименована в «⭐ Роль» (функция не менялась).
- `bot/handlers/members.py` — `cb_mem_nick_start` (запуск FSM, гейт `_check_admin`) →
  `fsm_mem_nick_enter` (валидация `validate_name`, `user_service.set_game_nick`,
  `sync_admin_title`, запись `AuditAction.MEMBER_NICK_CHANGE`, показ обновлённой карточки
  через существующую `member_card_kb`). Новых карточек/меню не создано.
- Это первый из 7 подэтапов плана «Этап 2.3 — Полный центр управления участником»
  (план и решение о поле target_id в audit_log подтверждены пользователем).

### Проверено
- `python3 -m py_compile` — 3 файла, без ошибок.
- Workflow Telegram Bot перезапущен, стартовал без ошибок, вебхук зарегистрирован.
- push выполнен: 2fb3f65 → e500502 → origin/main (подтверждено `git ls-remote origin main`).

## [1.2.8] — 2026-07-03 — Этап 2.2: редизайн раздела «Участники» (только интерфейс)

### Изменено (только UI, без изменений логики/ролей/Telegram API/прав доступа)
- `bot/handlers/members.py` — `_card_text()` переписана в единую функцию для карточки
  участника, используемую и в администрировании, и в режиме просмотра; добавлен параметр
  `stats_service` (очки активности через `user_activity`), добавлен показ Telegram-титула
  (`build_admin_title`); текст разбит на визуальные блоки, разделённые линиями ━━━.
  Обновлены все 3 вызова (`cb_memv_card`, `cb_mem_card`, `cb_mem_set`) — добавлена инъекция
  `stats_service: StatsService` как typed kwarg (уже доступен глобально через DI).
- `bot/keyboards/members.py` — `members_menu_kb()`: кнопки сгруппированы попарно по смыслу
  (Отчёт+Очистить, Синхронизация+Новый сезон); `member_card_kb()`: «Роль» и «Статистика»
  объединены в одну строку. Кнопки «⚙ Настройки» в разделе не было и не появилось.
- Поле «Сообщений» сознательно не добавлено — в проекте нет источника данных для счётчика
  сообщений; добавление было бы фиктивным значением.
- callback_data не менялись — навигация не затронута.

### Проверено
- `python3 -m py_compile` — оба файла, без ошибок.
- Проверены все вызовы `_card_text`, `member_card_kb`, `members_menu_kb`, `view_card_kb` —
  рассинхронизаций нет.
- Workflow Telegram Bot перезапущен, стартовал без ошибок, вебхук зарегистрирован.
- push выполнен: 8819c73 → 26de1fe → origin/main (подтверждено `git ls-remote origin main`).

## [1.2.8] — 2026-07-03 — Этап 1: исправление интерфейса и регистрации

### Изменено
- `bot/handlers/group.py` — восстановлен полный текст приветственного сообщения
  при вступлении в группу (был обрезан — отсутствовали разделы сообщества).
- `bot/handlers/news.py` — улучшено сообщение об отсутствии новостей:
  добавлен информационный текст вместо «Новостей пока нет.»
- `bot/handlers/content.py` — улучшены empty-state сообщения для всех разделов
  (события, гайды, скриншоты, мемы): добавлено поле empty_hint в _TYPES,
  каждый раздел показывает контекстную подсказку при отсутствии записей.
- `bot/handlers/rules.py` — добавлена константа _DEFAULT_RULES_CONTENT
  (сокращённая утверждённая версия правил клана из 8 пунктов);
  показывается автоматически если правила не опубликованы в БД.
- `bot/handlers/nick.py` — исправлен устаревший комментарий
  «только для администраторов» → «все роли, включая Участника».

### Проверено
- py_compile: OK для всех 5 изменённых файлов.
- Telegram Bot: RUNNING. API Server: RUNNING.

## [1.2.8] — 2026-07-03 — Регламент взаимодействия с пользователем: закреплён постоянный SOP

### Изменено (только документация, без изменений кода бота)
- `AGENT_START.md` — добавлен раздел «Регламент взаимодействия с пользователем»:
  8 постоянных правил (план перед крупными задачами, приоритет стабильности,
  согласование вариантов реализации, только функциональные предложения, запрет
  дублирования, формат ответов, обязательный отчёт, запрет «СТАТУС: выполнено»
  без GitHub); формат отчёта уточнён — все разделы обязательны.
- `replit.md` — раздел «User preferences» дополнен компактным сводом 8 правил
  регламента взаимодействия.
- `.agents/memory/dev_rules.md` — добавлен раздел 12 «Регламент взаимодействия
  с пользователем» с полным описанием всех 8 правил.
- `.agents/memory/workflow.md` — в SOP добавлен блок «Регламент взаимодействия
  с пользователем» с кратким сводом всех 8 правил.

### Проверено
- Код бота не изменялся — py_compile не требуется.
- Workflow: Telegram Bot RUNNING, API Server RUNNING.

## [1.2.8] — 2026-07-03 — Регламент разработки: закреплён постоянный SOP

### Изменено (только документация, без изменений кода бота)
- `AGENT_START.md` — добавлены разделы: обязательная проверка перед работой,
  разбивка задачи на этапы, управление кредитами, обновлён цикл сохранения (py_compile).
- `replit.md` — раздел «User preferences» обновлён: добавлены правила проверки
  перед работой, этапная разработка, управление кредитами, поведение при отсутствии Checkpoint.
- `.agents/memory/dev_rules.md` — добавлен раздел 11 «Регламент разработки»:
  проверка состояния, разбивка на этапы, цикл сохранения, управление кредитами.
- `.agents/memory/workflow.md` — SOP обновлён: добавлена обязательная проверка
  перед изменениями, этапная разработка, управление кредитами, py_compile в цикле сохранения.

### Проверено
- Код бота не изменялся — py_compile не требуется.
- Workflow: Telegram Bot RUNNING, API Server RUNNING.
- push выполнен: b2e8650 → origin/main.

## [1.2.8] — 2026-07-02 — UI polish: welcome flow, роли, карточка участника

### Изменено (только UI, без новой функциональности и архитектурных изменений)
- `bot/handlers/common.py` — добавлено интро-сообщение `_WELCOME_INTRO` перед мастером
  регистрации, но только для действительно новых пользователей (`is_new=True`);
  ветка `deep_join` не затронута (без интро, как раньше).
- `bot/utils/nick_format.py` — удалены `ROLE_NICK_TITLES`, `SEPARATOR`, легаси-титулы
  "Рекрут"/"Воин"; `build_full_nick()` теперь возвращает `"{symbol} {name}"`, символ берётся
  из `bot.utils.roles.ROLE_DISPLAY_ICONS` (✪ Лидер / ✦ Дитя клана / ✧ Старейшина / ◇ Участник).
- `bot/handlers/nick.py` — исправлены оставшиеся упоминания "Рекрут"/"Воин" в докстроке и
  тексте помощи `cb_how_to_rename`.
- `bot/handlers/members.py`, `bot/keyboards/members.py` — редизайн карточки участника:
  единая асинхронная `_card_text()` (использует `user_service` для дней в клане), новый
  порядок полей (имя / роль / игровой ник / Telegram / ID / дней в клане / статус);
  унифицированы иконки ролей через `ROLE_DISPLAY_ICONS`; добавлена кнопка «🗑 Удалить»
  в карточку участника (админ-раздел).
- `bot/handlers/synctitles.py` — логика `/synctitles` вынесена в переиспользуемую функцию
  `run_sync_titles()`; добавлена кнопка «🔄 Полная синхронизация» в меню «Участники»
  (`cb_mem_sync_titles`), вызывающая ту же функцию — без изменения бизнес-логики.

### Проверено
- `python3 -m py_compile` — все изменённые файлы, без ошибок.
- Изолированные unit-проверки (вне Telegram): `build_full_nick()` для всех 4 ролей,
  `_card_text()` на реальном пользователе из `data/astrum.db`, `register_if_new()` —
  подтверждена корректная ветка `is_new=True` только при первой регистрации.
- Полнотекстовый поиск "Рекрут" по `bot/` — 0 совпадений после исправлений.

## [1.2.6] — 2026-07-02 — Инфраструктурные правки (без изменения версии)

### Добавлено (документация/окружение, функционал бота не затронут)
- `pyproject.toml` — добавлена зависимость `aiosqlite==0.20.0` (отсутствовала после переноса на новый Replit-аккаунт).
- `replit.md`, `.agents/memory/dev_rules.md` — закреплён обязательный формат итогового отчёта
  (один блок ```text```, без markdown/HTML-таблиц, фиксированные поля ЗАДАНИЕ…ИТОГ).

## [1.2.6] — 2026-07-02 — Восстановление функционала + контроль игровых ников

### Добавлено

#### Модель (bot/models/audit.py)
- `AuditAction.SYNC_TITLES = "sync_titles"`
- `AuditAction.CLEAN_ABSENT = "clean_absent"`
- `AuditAction.NICK_REPORT = "nick_report"`
- `AuditAction.NICK_REMIND = "nick_remind"`
- Все новые actions добавлены в `CATEGORY_ACTIONS["members"]`

#### Клавиатуры (bot/keyboards/members.py)
- `MemberBtn.CLEAN_ABSENT = "mem:clean_absent"`
- `MemberBtn.CLEAN_ABSENT_OK = "mem:clean_absent_ok"`
- `MemberBtn.NICK_REPORT = "mem:nick_report"`
- `MemberBtn.NICK_REMIND = "mem:nick_remind"`
- `clean_absent_confirm_kb(count)` — подтверждение очистки
- `nick_report_kb()` — клавиатура отчёта по никам
- Обновлён `members_menu_kb()`: добавлены «📋 Детальный отчёт» и «🧹 Очистить отсутствующих»

#### Новый файл: bot/handlers/synctitles.py
- Команда `/synctitles` (только администраторы)
- Массовая синхронизация Telegram Admin Title через Bot API
- Проверка `getChatMember` для каждого участника
- Пропуск `creator` (владелец группы)
- Пропуск `left`/`kicked` участников
- `RetryAfter` + flood-control (asyncio.sleep 0.15с между запросами)
- Итоговый подробный отчёт (synced / skipped_creator / skipped_no_member / errors)
- Запись в `AuditAction.SYNC_TITLES`

#### Обработчики (bot/handlers/members.py)
- `cb_mem_clean_absent` — проверка через `getChatMember`, предварительный список
- `cb_mem_clean_absent_ok` — выполнение очистки (снятие прав, удаление из БД)
- `cb_mem_nick_report` — детальный отчёт: всего / с ником / без ника / списки
- `cb_mem_nick_remind` — публикация в тему «📢 Объявления» через `topic_service`

#### Защита в clean_absent:
- Суперпользователь (SUPERUSER_ID 8490615925) — защищён
- Владелец группы (статус `creator`) — защищён
- Участник с ролью LEADER — защищён
- Сам администратор (actor_id) — защищён

#### Точка входа (main.py)
- Импорт `synctitles` модуля
- Регистрация `synctitles.router` в private router (после members, до content)

---

## [1.2.5] — 2026-07-02 — Упрощение формата Telegram custom_title

### Изменено (финальная корректировка)
- `bot/utils/sync_title.py`:
  - `build_admin_title` упрощён: новый формат `{symbol} {game_nick}` (без текста роли).
  - Удалена константа `_SEP = " — "` (больше не используется).
  - `ADMIN_TITLES` обновлён: значения теперь только символы (`✪`, `✦`, `✧`, `◇`).
  - При смене роли меняется только символ слева.
  - При смене ника меняется только текст после символа.
  - Длинный ник усекается до 14 символов (2 символа занимают `{symbol} `).
- `bot/handlers/setrole.py`:
  - Импорт обновлён: `ADMIN_TITLES` → `build_admin_title`.
  - `tg_note` теперь строится через `build_admin_title(confirmed, target_nick)`.

## [1.2.4] — 2026-07-02 — Исправление генерации Telegram custom_title

### Исправлено (дефект AUD-007)
- `bot/utils/sync_title.py` — переписан `build_admin_title`.
- `bot/handlers/nick.py`, `setrole.py`, `group_nick.py`, `members.py` — обновлены call sites.

## [1.2.3] — 2026-07-02 — Финальная настройка окружения и постоянный цикл сохранения

### Изменено (инфраструктура)
- `scripts/push.sh` — поддержка двух имён токена.
- `AGENT_START.md`, `replit.md`, `dev_rules.md`, `workflow.md` — обновлены SOP.

## [1.2.2] — 2026-07-02 — Полировка меню «Участники»

### Добавлено
- `bot/keyboards/members.py` — `MemberViewBtn`, `view_list_kb`, `view_card_kb`.
- `bot/handlers/members.py` — обработчики `memv:list`, `memv:card`, `memv:noop`, `memv:close`.

## [1.2.1] — 2026-07-02 — Финальная полировка (полный аудит)

### Исправлено (критично)
- `bot/keyboards/main_menu.py` — восстановлены BTN.GUIDES/SCREENSHOTS/MEMES (AUD-004).

## [1.2.0] — 2026-07-02 — Полировка главного меню

### Изменено
- Новая раскладка главного меню 5×2.
