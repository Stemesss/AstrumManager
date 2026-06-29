---
name: Bot module structure
description: Canonical directory layout for the AstrumManager bot after modular refactor
---

## Layout (under `bot/`)

```
bot/
  config/          — settings.py (Config dataclass, load_config); __init__.py re-exports
  models/          — user.py: UserRole enum (Лидер/Старейшина/Дитя клана/Участник), User dataclass
  database/        — db.py: Database class wrapping aiosqlite; users table with WAL mode
  services/        — user_service.py: UserService (get_or_create, is_admin, set_role, get_all_users)
  keyboards/       — main_menu.py: BTN constants + MAIN_KEYBOARD ReplyKeyboardMarkup (8 buttons)
  utils/           — roles.py: role_label(role) → "👑 Лидер" style strings
  handlers/        — common.py, menu.py, admin.py, echo.py; registered in main.py in that order
  middlewares/     — logging.py: LoggingMiddleware
```

## Router registration order in main.py
common → admin → menu → echo (echo must be LAST — its catch-all fires for unknown text)

## Dependency injection
`dp["user_service"] = UserService(db)` in `build_dispatcher()`; handlers declare `user_service: UserService` as a kwarg and aiogram injects it automatically.

## Admin access
`UserRole.admin_roles()` returns `{LEADER, ELDER}`. `UserService.is_admin(telegram_id)` checks this.

**Why:** Keeps role logic in one place (models/user.py) — no scattered if-chains across handlers.
