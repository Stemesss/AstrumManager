# AstrumManager — Telegram Bot

**VERSION: 1.2.8 | STATUS: STABLE**

> Читать перед работой: [`AGENT_START.md`](AGENT_START.md)

A Python Telegram bot for clan management, built with aiogram 3, running in webhook mode on Replit and Railway, with polling fallback for local development.

## Run & Operate

- `python3 main.py` — start the bot (auto-detects webhook vs polling mode)
- `pnpm --filter @workspace/api-server run dev` — run the Node.js API server (proxies Telegram webhook to the Python bot)
- `pnpm run typecheck` — full TypeScript typecheck across all packages

## Git Scripts

- `bash scripts/push.sh` — push current main branch to GitHub via `GITHUB_TOKEN`; shows commit list and result
- `bash scripts/pull.sh` — fetch latest changes from GitHub, check for conflicts, apply fast-forward merge

## Stack

- **Bot:** Python 3.11, aiogram 3, aiohttp, aiosqlite
- **Proxy:** Node.js 24, Express 5, http-proxy-middleware
- **Workspace:** pnpm monorepo, TypeScript 5.9

## Where things live

- `main.py` — single entry point; runs webhook mode on Replit/Railway, polling locally
- `bot/config/settings.py` — Config dataclass, load_config
- `bot/handlers/` — one file per section (admin, news, nick, members, etc.)
- `bot/services/` — UserService, AuditService, StatsService, NewsService, TopicService
- `bot/database/db.py` — Database class (aiosqlite, WAL mode)
- `bot/middlewares/logging.py` — logs every incoming update
- `bot/middlewares/nick_gate.py` — blocks unregistered users
- `artifacts/api-server/src/routes/telegram.ts` — proxies `/api/telegram/webhook` → Python bot on port 6000

## Architecture decisions

- **Webhook over polling:** Replit blocks outbound connections to Telegram's servers, so polling is impossible. The bot registers a webhook URL on startup and receives updates via HTTP POST.
- **Two-process design:** The Python bot (aiohttp, port 6000) runs alongside a Node.js Express server (port 8080). Express proxies `/api/telegram/webhook` to the Python bot so Telegram can reach it through the shared Replit proxy.
- **Auto-detection in main.py:** `resolve_public_host()` checks `WEBHOOK_BASE_URL` → `REPLIT_DOMAINS` → `RAILWAY_PUBLIC_DOMAIN` in order. Falls back to polling if none is set (useful for local dev).
- **Port on Railway:** `main.py` respects `$PORT` (Railway's injected port) first, then `$WEBHOOK_PORT`, then defaults to 6000.
- **Scores on-the-fly:** Activity points computed from `audit_log`, not stored separately. Formula: news_create=5, guide_create=10, screenshot_upload=2, event_create=8.

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

- После каждого задания агент обязан автоматически обновлять файлы памяти проекта без отдельной команды.
- Перед любым изменением — обязательная проверка: HEAD, origin/main, версия, git status, статус workflow. До окончания проверки ничего не изменять.
- Любая задача разбивается на подэтапы, сгруппированные в логические блоки (2–3 связанных подэтапа или не более 6 изменённых файлов за блок). Цикл сохранения выполняется не после каждого подэтапа, а после завершения логического блока: py_compile → тесты → workflow → Checkpoint → push → проверка origin/main. Только после успешного push — переход к следующему блоку.
- Если кредиты могут закончиться — не начинать следующий этап; завершить текущий, дождаться Checkpoint, выполнить push, отправить отчёт.
- Если Checkpoint отсутствует — не выполнять новые изменения; сообщить: «Ожидаю автоматический Replit Checkpoint для завершения цикла сохранения.»
- После каждого завершённого задания — полный цикл сохранения (см. AGENT_START.md): память → py_compile → smoke-test → workflow → checkpoint → push → проверка GitHub.
- Итоговый отчёт — ВСЕГДА один блок ```text``` (для кнопки «Копировать» в интерфейсе Replit), строго в формате: ЗАДАНИЕ / СТАТУС / ВЕРСИЯ / ЭТАП / ИЗМЕНЕНИЯ / ФАЙЛЫ / ПРОВЕРКА / ТЕСТЫ / WORKFLOW / GIT / GITHUB / ПАМЯТЬ / ИТОГ. Все разделы обязательны — ни один не пропускать.
- ВСЕ ответы агента — только обычный текст. Все отчёты, планы, задания и списки — исключительно в одном блоке ```text``` с кнопкой «Скопировать». Запрещены: карточки Replit, Plan, Canvas, интерактивные блоки, таблицы, раскрывающиеся списки, любые форматы, которые нельзя скопировать целиком одним нажатием.
- Если push НЕ выполнен — запрещено писать «СТАТУС: выполнено».
- scripts/push.sh поддерживает два имени токена: GITHUB_TOKEN и AstrumManagerMain (приоритет у GITHUB_TOKEN).
- РЕГЛАМЕНТ ВЗАИМОДЕЙСТВИЯ (постоянный): (1) Перед крупной задачей (>4 файлов / несколько логических частей / архитектурные изменения) — сначала показать план, остановиться, ждать подтверждения. (2) Ошибка/регрессия — стоп, сначала исправить, потом новый функционал. (3) Несколько вариантов реализации — предложить пользователю, не выбирать самостоятельно. (4) Предлагать только функции AstrumManager, не предлагать Deploy/Git/ENV/Infrastructure без запроса. (5) Перед новой функцией проверить существующий функционал — расширять, не дублировать. (6) Формат ответов — только текст, один блок text. (7) После каждого этапа — полный отчёт, все разделы. (8) «СТАТУС: выполнено» — только после синхронизации origin/main.

## Pointers

- See [`AGENT_START.md`](AGENT_START.md) for mandatory reading order before any work
- See [`PROJECT_HISTORY.md`](PROJECT_HISTORY.md) for full stage history
- See `.agents/memory/` for all agent memory files
