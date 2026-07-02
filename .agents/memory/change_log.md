---
name: Change log
description: Журнал изменений — обновляется после каждого выполненного задания
---

# Журнал изменений

## [1.2.0] — 2026-07-02 — Полировка главного меню

### Удалено
- `bot/keyboards/main_menu.py` — кнопки «😂 Мемы», «📚 Гайды», «📸 Скриншоты» из BTN и из MAIN_KEYBOARD
- `bot/handlers/menu.py` — строки «Гайды», «Скриншоты», «Мемы» из текста справки

### Изменено
- `bot/keyboards/main_menu.py` — новая раскладка 5×2: Новости/События | Правила/Жалобы | Участники/Администрация | Журнал/Статистика | Профиль/Помощь

## [1.1.0] — 2026-07-02 — Полировка раздела «Участники»

### Изменено
- `bot/utils/roles.py` — ROLE_ORDER: LEADER→ELDER→CLAN_CHILD→MEMBER
- `bot/keyboards/members.py` — иконки ✪✦✧◇→👑🛡⭐👤; убрана кнопка ⚙️
- `bot/handlers/members.py` — иконки ✪✦✧◇→👑🛡⭐👤; фильтр game_nick в _show_list()

## [1.0.2] — 2026-07-02 — Безопасность webhook

### Добавлено
- `bot/config/settings.py` — поле webhook_secret (WEBHOOK_SECRET env или auto-generated)
- `main.py` — secret_token в set_webhook и SimpleRequestHandler

## [1.0.1] — 2026-07-02 — Git-скрипты

### Добавлено
- `scripts/push.sh`, `scripts/pull.sh`
