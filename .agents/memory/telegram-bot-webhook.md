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
- Node.js Express (port 8081→80, exposed publicly) proxies `/tg/webhook` to the Python bot
- Express must skip `json()` body parsing for `/tg` routes — consuming the body before the proxy kills the request

**Why:** Replit's shared proxy only exposes services registered in `artifact.toml`. The Python bot can't be directly registered as a service artifact, so it rides behind the existing Node.js API server.

**Port on Railway:** `main.py` reads `$PORT` first (Railway injects it), then `$WEBHOOK_PORT`, then defaults to 6000.

**Critical gotcha — `/api` prefix is reserved on Replit's dev-domain edge:** any request to `<repl>.replit.dev/api/*` gets a silent 502 from Replit's own edge proxy, before it ever reaches the app — even though the exact same path works fine when curled directly against the local port. There is no error in app logs because the request never arrives. Symptom: webhook shows "registered successfully" and `getWebhookInfo` shows `last_error_message: "Wrong response from the webhook: 502 Bad Gateway"`, while direct localhost curls to the same path succeed. Fix: never mount webhook/callback endpoints that must be reachable from outside under `/api` on the dev domain — use a different top-level prefix (this project uses `/tg/webhook`). Confirmed via `getWebhookInfo`, `curl -v` on multiple `/api/*` subpaths (all 502) vs. non-`/api` paths (correct 404), matching response headers (missing `x-powered-by: Express` on the 502s meant Replit's edge answered, not the app).
