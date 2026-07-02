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

## AUD-007 — Неверный формат Telegram custom_title

```
ID:        AUD-007
Дата:      2026-07-02
Статус:    исправлен
Приоритет: high
Описание:  build_admin_title генерировал формат «Воин | Ник» вместо
           требуемого «✦ Ник — Дитя клана». MEMBER не получал custom_title
           (понижался до обычного участника). Источник имени был неопределён
           (в setrole.py game_nick не передавался в sync_admin_title).
Причина:   Первоначальная реализация использовала другой формат (роль первой,
           потом ник через ASCII-разделитель). Требования были изменены.
Решение:   Полностью переписан build_admin_title в sync_title.py:
           новый формат {symbol} {game_nick} — {role_label} для всех 4 ролей.
           MEMBER теперь тоже получает promote + custom_title.
           setrole.py передаёт game_nick в sync_admin_title.
           Удалены guard-проверки if role not in ADMIN_TITLES в nick.py и group_nick.py.
Файлы:    bot/utils/sync_title.py, bot/handlers/nick.py,
          bot/handlers/setrole.py, bot/handlers/group_nick.py,
          bot/handlers/members.py
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
Решение:   Установлены через pip: aiogram, aiohttp, aiosqlite, aiofiles,
           python-dotenv, pydantic, magic-filter.
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

## AUD-004 — AttributeError: BTN.GUIDES при импорте content.py

```
ID:        AUD-004
Дата:      2026-07-02
Статус:    исправлен
Приоритет: critical
Описание:  Бот падал при старте с "AttributeError: type object 'BTN' has no
           attribute 'GUIDES'" — бот вообще не запускался.
Причина:   Константы BTN.GUIDES/SCREENSHOTS/MEMES удалены из класса BTN
           вместе с кнопками из MAIN_KEYBOARD в v1.2.0.
Решение:   Константы восстановлены в BTN (не в MAIN_KEYBOARD).
Файлы:     bot/keyboards/main_menu.py
```

---

## AUD-005 — Дублирующиеся зависимости в requirements.txt

```
ID:        AUD-005
Дата:      2026-07-02
Статус:    исправлен
Приоритет: low
Описание:  requirements.txt содержал повторный блок из 7 зависимостей.
Решение:   Дубликаты удалены.
Файлы:     requirements.txt
```

---

## AUD-006 — Дублирующаяся константа _SUPERUSER в members.py

```
ID:        AUD-006
Дата:      2026-07-02
Статус:    исправлен
Приоритет: low
Описание:  Локальная константа _SUPERUSER дублировала _SUPERUSER_ID.
Решение:   Локальная константа удалена.
Файлы:     bot/handlers/members.py
```

---

## ОЖИДАЕМЫЕ (НЕ ДЕФЕКТЫ)

- `TelegramBadRequest: chat not found` в логах после smoke-тестов —
  нормально: фейковые chat_id не могут получать ответы.
  (см. `.agents/memory/smoke-test-errors.md`)
