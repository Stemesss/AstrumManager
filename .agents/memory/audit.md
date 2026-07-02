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

## AUD-004 — AttributeError: BTN.GUIDES при импорте content.py (бот не запускался)

```
ID:        AUD-004
Дата:      2026-07-02
Статус:    исправлен
Приоритет: critical
Описание:  Бот падал при старте с "AttributeError: type object 'BTN' has no
           attribute 'GUIDES'" при импорте bot.handlers.content — бот вообще
           не запускался.
Причина:   При полировке главного меню (v1.2.0) константы BTN.GUIDES,
           BTN.SCREENSHOTS, BTN.MEMES были удалены из класса BTN целиком
           вместе с кнопками из MAIN_KEYBOARD. Но bot/handlers/content.py
           использует эти константы как ключи конфигурации разделов (_TYPES)
           и как текстовые точки входа (@router.message(F.text == BTN.X)) —
           удаление констант сломало импорт всего модуля.
Решение:   Константы BTN.GUIDES/SCREENSHOTS/MEMES восстановлены в классе BTN
           (с комментарием о причине), но НЕ возвращены в MAIN_KEYBOARD —
           раскладка меню v1.2 сохранена, функциональность разделов
           «Гайды/Скриншоты/Мемы» восстановлена (доступна из админ-панели и
           текстовых точек входа).
Файлы:     bot/keyboards/main_menu.py
```

---

## AUD-005 — Дублирующиеся зависимости в requirements.txt

```
ID:        AUD-005
Дата:      2026-07-02
Статус:    исправлен
Приоритет: low
Описание:  requirements.txt содержал повторный блок из 7 зависимостей
           (aiofiles, aiogram, aiohttp, aiosqlite, magic-filter, pydantic,
           python-dotenv) — не критично для pip, но замусоривало файл.
Причина:   Дублирование при предыдущих правках зависимостей.
Решение:   Дубликаты удалены, оставлен один отсортированный список.
Файлы:     requirements.txt
```

---

## AUD-006 — Дублирующаяся константа _SUPERUSER в members.py

```
ID:        AUD-006
Дата:      2026-07-02
Статус:    исправлен
Приоритет: low
Описание:  В cb_mem_del_card была локальная константа _SUPERUSER = 8490615925,
           дублирующая уже существующую модульную _SUPERUSER_ID (та же
           логика защиты суперпользователя, два источника истины).
Причина:   Не переиспользована существующая константа при добавлении проверки.
Решение:   Локальная константа удалена, используется _SUPERUSER_ID.
Файлы:     bot/handlers/members.py
```

---

## Мелкие правки качества кода (не дефекты уровня приложения)

- Удалены неиспользуемые импорты (pyflakes): MAIN_KEYBOARD, StateFilter,
  UserRole, ROLE_ORDER, ADMIN_PANEL_KB, TopicBtn/topics_menu_kb,
  build_full_nick, dataclasses.field — файлы: admin.py, audit.py, content.py,
  news.py, rules.py, icons.py, members.py, menu.py, publish.py, topics.py,
  bot/keyboards/members.py, bot/models/topic.py.
- Исправлены 3 f-строки без плейсхолдеров (без функционального эффекта):
  complaints.py, nick.py, content.py.

## Проверено и подтверждено корректным (ложные срабатывания при ручном аудите)

- `bot/keyboards/topics.py` / `bot/handlers/topics.py` — TopicBtn.PREFIX = "topic:",
  обработчик `F.data.startswith(TopicBtn.PREFIX)` корректно перехватывает все
  callback выбора ветки. Дублирования маршрутов нет.
- `bot/keyboards/members.py` / `bot/handlers/members.py` — обработчик
  `mem:del_card:{uid}` зарегистрирован и работает.
- `bot/handlers/rules.py` — обработчик `rul:edit:{id}` зарегистрирован и
  реализован полностью (не обрезан).
- Все 21 роутер из `bot/handlers/` зарегистрированы в `main.py` в правильном
  порядке (порядок соответствует `dev_rules.md`, раздел 4).
- SQL-запросы в `bot/database/db.py` — параметризованы (`?`), f-строки
  используются только для генерации `?`-плейсхолдеров, инъекций нет.
- `bot/handlers/stats.py` и `bot/handlers/statistics.py` — дублируют друг
  друга функционально (два входа в статистику: reply-кнопка «Статистика» и
  админ-панель), но оба полностью рабочие и не конфликтуют по callback_data
  (`stats:` vs `statx:`/`admin:statistics`). Не дефект, но кандидат на
  объединение при следующем крупном рефакторинге (не выполнено — не входит в
  рамки «исправить недочёты без удаления функциональности»).
- `bot/handlers/debug.py` — временный обработчик `/threadid`, помечен
  собственным докстрингом "удалить после проверки веток"; не тронут, так как
  удаление функциональности не входит в рамки задания без явного подтверждения.

---

## ОЖИДАЕМЫЕ (НЕ ДЕФЕКТЫ)

- `TelegramBadRequest: chat not found` в логах после smoke-тестов —
  нормально: фейковые chat_id не могут получать ответы.
  (см. `.agents/memory/smoke-test-errors.md`)
