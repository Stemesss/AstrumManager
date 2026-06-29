---
name: Smoke test false errors
description: Why "chat not found" appears in logs after smoke tests and why it is harmless
---

## What happens
Smoke tests POST fake Telegram updates with `chat.id = 111` and `from.id = 111`.  
The bot processes them correctly (returns HTTP 200) but then tries to call `sendMessage` back to chat 111, which does not exist on Telegram's servers. Telegram returns `400 Bad Request: chat not found`.

## Is it a bug?
No. HTTP 200 from the webhook endpoint means aiogram accepted and handled the update. The `TelegramBadRequest` is the expected consequence of sending replies to a nonexistent chat.

## How to avoid during testing
Use a real Telegram user ID for chat/from if you need end-to-end reply verification.  
For handler routing tests (does the right handler fire?), the current approach is sufficient.

**Why recorded:** The error looks alarming in logs but is a known testing artifact, not a production issue.
