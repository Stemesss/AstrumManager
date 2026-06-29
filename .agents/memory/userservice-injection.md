---
name: UserService injection pattern
description: How UserService (and other services) are injected into aiogram handlers
---

## Pattern

In `build_dispatcher()` in `main.py`:
```python
user_service = UserService(db)
dp["user_service"] = user_service
```

In any handler:
```python
async def handle_start(message: Message, user_service: UserService) -> None:
    ...
```

aiogram 3 reads the kwarg name, looks it up in the dispatcher's data dict, and injects it automatically.

## Why this approach
- No global singletons — easy to test by swapping the value in `dp[]`.
- db and user_service both live in `dp[]` so any handler can declare either.
- Database connection lifecycle is managed in `on_startup`/`on_shutdown` hooks, not at module import time.

**Why:** aiogram 3's FSM/data injection is the idiomatic DI mechanism; avoids circular imports and module-level state.
