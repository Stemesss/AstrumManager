---
name: Change log
description: Журнал изменений — обновляется после каждого выполненного задания
---

# Журнал изменений

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
