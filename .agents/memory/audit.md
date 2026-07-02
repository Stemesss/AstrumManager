---
name: Audit log
description: Журнал найденных и исправленных дефектов — обновляется при обнаружении/исправлении бага
---

# Журнал дефектов (Audit)

## Формат записи

```
ID:       AUD-NNN
Дата:     YYYY-MM-DD
Статус:   найден | исправлен | отклонён
Приоритет: critical | high | medium | low
Описание: ...
Причина:  ...
Решение:  ...
Файлы:    ...
```

---

## AUD-001 — ModuleNotFoundError при запуске бота

```
ID:        AUD-001
Дата:      2026-07-02
Статус:    исправлен
Приоритет: critical
Описание:  Бот падал при старте с ошибкой "No module named 'aiogram'"
           после миграции на новую среду Replit.
Причина:   Python-зависимости не были установлены в новой среде.
Решение:   Установлены через installLanguagePackages:
           aiogram, aiohttp, aiosqlite, aiofiles, python-dotenv,
           pydantic, magic-filter.
Файлы:     requirements.txt, pyproject.toml
```

---

## AUD-002 — ERR_MODULE_NOT_FOUND esbuild при запуске API Server

```
ID:        AUD-002
Дата:      2026-07-02
Статус:    исправлен
Приоритет: critical
Описание:  API Server падал с "Cannot find package 'esbuild'"
           после миграции на Replit.
Причина:   node_modules отсутствовали в новой среде.
Решение:   pnpm install --no-frozen-lockfile
Файлы:     artifacts/api-server/package.json, pnpm-lock.yaml
```

---

## AUD-003 — vite: not found при запуске Component Preview Server

```
ID:        AUD-003
Дата:      2026-07-02
Статус:    исправлен
Приоритет: high
Описание:  Mockup sandbox падал с "sh: 1: vite: not found".
Причина:   node_modules отсутствовали (та же причина, что AUD-002).
Решение:   pnpm install — установил vite вместе с остальными пакетами.
Файлы:     artifacts/mockup-sandbox/package.json
```

---

## ОЖИДАЕМЫЕ (НЕ ДЕФЕКТЫ)

- `TelegramBadRequest: chat not found` в логах после smoke-тестов —
  нормально: фейковые chat_id не могут получать ответы.
  (см. `.agents/memory/smoke-test-errors.md`)
