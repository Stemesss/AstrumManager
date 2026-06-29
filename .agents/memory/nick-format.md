---
name: Nick format and storage
description: How game nicks are stored and displayed — separate name vs full formatted nick
---

## Storage model

`game_nick` DB column stores **only the name part** (e.g., "Вадим").
Full displayed nick is **computed on the fly**: `build_full_nick(name, role)` → "🌟 Рекрут｜Вадим".

**Why:** When a user's role changes, the title prefix updates automatically — no DB write needed.

## Title mapping (bot/utils/nick_format.py)

```
ROLE_NICK_TITLES:
  LEADER     → "👑 Лидер"
  CLAN_CHILD → "⚔️ Воин"
  ELDER      → "🛡️ Старейшина"
  MEMBER     → "🌟 Рекрут"
```

Separator: `｜` (U+FF5C fullwidth vertical line, not `|`)

## How to apply

Anywhere you want to show the user's nick to them, call `build_full_nick(name, role)`.
`name` comes from `user_service.get_game_nick(uid)` or `user.game_nick`.
`role` comes from `user_service.get_role(uid)`.

In audit log descriptions, prefer the full nick for readability.
In admin members lists, the name-only display is acceptable.

## NickGate middleware

`bot/middlewares/nick_gate.py` intercepts all private messages from users without a nick.
Skips: commands (`/`), any NickSetup FSM state.
Registered on `private.message` (not the global dp.update level).
