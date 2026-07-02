---
name: Change log
description: Журнал изменений — обновляется после каждого выполненного задания
---

# Журнал изменений

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
