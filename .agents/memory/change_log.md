---
name: Change log
description: Журнал изменений — обновляется после каждого выполненного задания
---

# Журнал изменений

## [1.1.0] — 2026-07-02 — Полировка раздела «Участники»

### Изменено
- `bot/utils/roles.py` — ROLE_ORDER: LEADER → ELDER → CLAN_CHILD → MEMBER (было LEADER → CLAN_CHILD → ELDER → MEMBER)
- `bot/keyboards/members.py` — иконки ролей в списке: ✪✦✧◇ → 👑🛡⭐👤; убрана кнопка ⚙️ из каждой строки списка
- `bot/handlers/members.py` — иконки ролей: ✪✦✧◇ → 👑🛡⭐👤; фильтр `game_nick` в `_show_list()` — показываются только участники с установленным ником

### Не изменено
- callback_data всех кнопок
- бизнес-логика, БД, права
- карточка участника

## [1.0.2] — 2026-07-02 — Безопасность webhook + установка на Replit

### Добавлено
- `bot/config/settings.py` — поле `webhook_secret`, генерируется из `WEBHOOK_SECRET` env или `secrets.token_hex(32)`
- `main.py` — `set_webhook(secret_token=...)` и `SimpleRequestHandler(secret_token=...)`

## [1.0.1] — 2026-07-02 — Git-скрипты

### Добавлено
- `scripts/push.sh` — push в GitHub через GITHUB_TOKEN; показывает список коммитов и результат
- `scripts/pull.sh` — информирует о состоянии и объясняет ограничение pull в среде Replit

### Изменено
- `replit.md` — добавлен раздел "Git Scripts"
- `PROJECT_HISTORY.md` — добавлена запись о git-скриптах и GITHUB_TOKEN

### Замечания
- git pull/fetch заблокированы платформой Replit (пишут в .git/objects/)
- git push работает штатно через прямой URL с токеном
