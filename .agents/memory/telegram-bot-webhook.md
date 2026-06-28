---
name: Telegram bot webhook architecture
description: Why polling is blocked on Replit and how the two-process webhook setup works.
---

# Telegram Bot Webhook Architecture

Replit blocks outbound connections to `api.telegram.org`, so `dp.start_polling()` always fails with `ConnectionResetError`.

**How to apply:** Always use webhook mode on Replit (and Railway). The entry point `main.py` auto-detects via `resolve_public_host()`:
1. `WEBHOOK_BASE_URL` env var (explicit override)
2. `REPLIT_DOMAINS` (Replit)
3. `RAILWAY_PUBLIC_DOMAIN` (Railway)
4. Falls back to polling only when none are set (local dev)

**Two-process design:**
- Python bot (aiohttp) listens on port 6000 (internal, not exposed by proxy)
- Node.js Express (port 8080, exposed at `/api`) proxies `/api/telegram/webhook` to the Python bot
- Express must skip `json()` body parsing for `/api/telegram` routes — consuming the body before the proxy kills the request

**Why:** Replit's shared proxy only exposes services registered in `artifact.toml`. The Python bot can't be directly registered as a service artifact, so it rides behind the existing Node.js API server.

**Port on Railway:** `main.py` reads `$PORT` first (Railway injects it), then `$WEBHOOK_PORT`, then defaults to 6000.
