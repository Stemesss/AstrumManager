# Telethon Session Setup

This document describes how to generate a Telethon `StringSession` for future
full member synchronization in AstrumManager.

---

## 1. Obtain API credentials from Telegram

1. Open [https://my.telegram.org](https://my.telegram.org) and log in with your
   Telegram account.
2. Go to **API development tools**.
3. Create a new application (name and platform do not matter).
4. Copy the values shown:
   - **App api_id** → this is your `TELEGRAM_API_ID` (a number, e.g. `12345678`)
   - **App api_hash** → this is your `TELEGRAM_API_HASH` (a hex string)

---

## 2. Add Secrets to Replit

Open the **Secrets** tab in the Replit sidebar (lock icon) and add:

| Secret name        | Value                          |
|--------------------|--------------------------------|
| `TELEGRAM_API_ID`  | The integer App api_id         |
| `TELEGRAM_API_HASH`| The hex App api_hash string    |

Both values are required. The utility will exit with a clear error message if
either is missing.

---

## 3. Run the session generator

Open the **Shell** tab in Replit and run:

```
python tools/generate_telethon_session.py
```

The utility will:

1. Validate that `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` are set.
2. Ask for your **phone number** in international format (e.g. `+79001234567`).
3. Ask for the **login code** sent by Telegram to that phone number.
4. Ask for your **2FA password** only if two-step verification is enabled on
   your account.
5. Print the generated `StringSession` string to the terminal.

---

## 4. Store the generated session

After the utility prints the session string:

1. Copy the **entire** printed string (it starts with `1` and is ~350 characters long).
2. Open the **Secrets** tab in Replit.
3. Create a new Secret:

| Secret name        | Value                          |
|--------------------|--------------------------------|
| `TELETHON_SESSION` | The copied StringSession string|

The utility does **not** save the session automatically — you must copy and
store it manually.

---

## 5. Security rules

- **NEVER** commit the `StringSession` string to GitHub or any version control.
- **NEVER** share it in chat logs, issues, or pull requests.
- The `.gitignore` already excludes `*.session` files, but a `StringSession` is
  a plain string — it has no file to exclude. Guard it as you would a password.
- If the session is ever compromised, revoke it immediately via
  [https://my.telegram.org](https://my.telegram.org) → **Active sessions**.

---

## Summary

```
Step 1  →  my.telegram.org → get api_id and api_hash
Step 2  →  Replit Secrets: set TELEGRAM_API_ID and TELEGRAM_API_HASH
Step 3  →  Shell: python tools/generate_telethon_session.py
Step 4  →  Replit Secrets: store result as TELETHON_SESSION
```
