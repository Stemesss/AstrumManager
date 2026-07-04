# -*- coding: utf-8 -*-
"""
Standalone utility to generate a Telethon StringSession.

Reads TELEGRAM_API_ID and TELEGRAM_API_HASH from environment/Replit Secrets.
Prints the generated StringSession to stdout.
Does NOT save the session automatically.
"""
import asyncio
import os
import sys


def _get_secret(name: str) -> str | None:
    return os.getenv(name, "").strip() or None


def _validate_secrets() -> tuple[int, str]:
    api_id_raw = _get_secret("TELEGRAM_API_ID")
    api_hash = _get_secret("TELEGRAM_API_HASH")

    missing = []
    if not api_id_raw:
        missing.append("TELEGRAM_API_ID")
    if not api_hash:
        missing.append("TELEGRAM_API_HASH")

    if missing:
        print("ERROR: The following Replit Secrets are missing or empty:")
        for name in missing:
            print(f"  • {name}")
        print()
        print("Add them in the Replit Secrets tab, then run this utility again.")
        print("See docs/telethon_setup.md for instructions.")
        sys.exit(1)

    try:
        api_id = int(api_id_raw)
    except ValueError:
        print(f"ERROR: TELEGRAM_API_ID must be an integer, got: {api_id_raw!r}")
        sys.exit(1)

    return api_id, api_hash


async def generate_session() -> None:
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    api_id, api_hash = _validate_secrets()

    print("=== Telethon StringSession Generator ===")
    print()

    session = StringSession()
    client = TelegramClient(session, api_id, api_hash)

    await client.connect()

    phone = input("Enter your phone number (international format, e.g. +79001234567): ").strip()
    await client.send_code_request(phone)

    code = input("Enter the login code you received from Telegram: ").strip()

    try:
        await client.sign_in(phone, code)
    except Exception as e:
        error_type = type(e).__name__
        if "SessionPasswordNeeded" in error_type or "two-step" in str(e).lower():
            password = input("Enter your 2FA password: ").strip()
            await client.sign_in(password=password)
        else:
            print(f"ERROR during sign-in: {e}")
            await client.disconnect()
            sys.exit(1)

    generated = client.session.save()
    await client.disconnect()

    print()
    print("=== SUCCESS ===")
    print()
    print("Your StringSession (copy the full line below):")
    print()
    print(generated)
    print()
    print("Store this value in the Replit Secret named TELETHON_SESSION.")
    print("NEVER commit this string to GitHub.")


def main() -> None:
    try:
        asyncio.run(generate_session())
    except KeyboardInterrupt:
        print()
        print("Cancelled by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
