# Telegram Bot

A Python Telegram bot built with aiogram 3, running in webhook mode on Replit and Railway, with polling fallback for local development.

## Run & Operate

- `python3 main.py` — start the bot (auto-detects webhook vs polling mode)
- `pnpm --filter @workspace/api-server run dev` — run the Node.js API server (proxies Telegram webhook to the Python bot)
- `pnpm run typecheck` — full TypeScript typecheck across all packages

## Stack

- **Bot:** Python 3.11, aiogram 3, aiohttp
- **Proxy:** Node.js 24, Express 5, http-proxy-middleware
- **Workspace:** pnpm monorepo, TypeScript 5.9

## Where things live

- `main.py` — single entry point; runs webhook mode on Replit/Railway, polling locally
- `bot/config.py` — loads `TELEGRAM_BOT_TOKEN` from env
- `bot/handlers/common.py` — /start, /help, /about commands
- `bot/handlers/echo.py` — /echo command + fallback handler
- `bot/middlewares/logging.py` — logs every incoming update
- `artifacts/api-server/src/routes/telegram.ts` — proxies `/api/telegram/webhook` → Python bot on port 6000

## Architecture decisions

- **Webhook over polling:** Replit blocks outbound connections to Telegram's servers, so polling is impossible. The bot registers a webhook URL on startup and receives updates via HTTP POST.
- **Two-process design:** The Python bot (aiohttp, port 6000) runs alongside a Node.js Express server (port 8080). Express proxies `/api/telegram/webhook` to the Python bot so Telegram can reach it through the shared Replit proxy.
- **Auto-detection in main.py:** `resolve_public_host()` checks `WEBHOOK_BASE_URL` → `REPLIT_DOMAINS` → `RAILWAY_PUBLIC_DOMAIN` in order. Falls back to polling if none is set (useful for local dev).
- **Port on Railway:** `main.py` respects `$PORT` (Railway's injected port) first, then `$WEBHOOK_PORT`, then defaults to 6000.

## Environment variables

- `TELEGRAM_BOT_TOKEN` *(secret, required)* — from @BotFather on Telegram
- `WEBHOOK_BASE_URL` *(optional)* — override the public webhook base URL (e.g. `https://yourdomain.com`)
- `WEBHOOK_PORT` *(optional, default 6000)* — internal port the Python bot listens on
- `PORT` *(Railway-managed)* — used instead of `WEBHOOK_PORT` when set

## Deploying to Railway

1. Set `TELEGRAM_BOT_TOKEN` as a Railway secret.
2. Set `WEBHOOK_BASE_URL` to your Railway public URL (e.g. `https://mybot.up.railway.app`) **or** Railway's `RAILWAY_PUBLIC_DOMAIN` env var is picked up automatically.
3. The run command is: `python3 main.py`

## Gotchas

- On Replit, polling is blocked at the network level. Always use webhook mode.
- The Node.js API server must be running alongside the Python bot on Replit — it is the public face that receives Telegram's HTTPS POST and forwards it to the Python process.
- Express's `json()` middleware is skipped for `/api/telegram` paths to avoid consuming the request body before the proxy can forward it.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
