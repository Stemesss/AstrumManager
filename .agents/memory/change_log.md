---
name: Change log
description: Журнал изменений — обновляется после каждого выполненного задания
---

# Журнал изменений

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
- `bot/utils/sync_title.py` — переписан `build_admin_title`:
  - Удалён формат «Воин | Ник». Введён формат «{symbol} {nick} — {role}».
  - `ADMIN_TITLES` расширен до всех 4 ролей (включая MEMBER).
  - `sync_admin_title` — MEMBER теперь получает кастомный титул.
- `bot/handlers/nick.py` — убрана проверка `if role not in ADMIN_TITLES`.
- `bot/handlers/setrole.py` — `sync_admin_title` теперь передаёт `game_nick`.
- `bot/handlers/group_nick.py` — убрана проверка `if role in ADMIN_TITLES`.
- `bot/handlers/members.py` — убрана мёртвая ветка «Telegram-титул снят».

## [1.2.3] — 2026-07-02 — Финальная настройка окружения и постоянный цикл сохранения

### Изменено (инфраструктура, не функциональность бота)
- `scripts/push.sh` — поддержка двух имён токена: GITHUB_TOKEN / AstrumManagerMain.
- `AGENT_START.md` — добавлен «ОБЯЗАТЕЛЬНЫЙ ЦИКЛ СОХРАНЕНИЯ».
- `replit.md` — обновлены User preferences.
- `.agents/memory/dev_rules.md` — добавлен раздел «Обязательный цикл».
- `.agents/memory/workflow.md` — SOP «Выполнение задания» обновлён.

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
