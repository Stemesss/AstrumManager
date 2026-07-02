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

## AUD-008 — Формат custom_title содержал текст роли (требовался только символ + ник)

```
ID:        AUD-008
Дата:      2026-07-02
Статус:    исправлен
Приоритет: high
Описание:  build_admin_title (v1.2.4) генерировал «✪ Вадим — Лидер».
           Текст роли занимал место и из-за ограничения 16 символов
           ник обрезался до 1 символа для ролей «Дитя клана»/«Старейшина».
Причина:   Требования были скорректированы: нужен только символ + ник.
Решение:   build_admin_title упрощён до формата «{symbol} {game_nick}».
           Ник теперь занимает до 14 символов (2 = символ + пробел).
           Удалена константа _SEP. ADMIN_TITLES сокращён до символов.
Файлы:    bot/utils/sync_title.py, bot/handlers/setrole.py
```

---

## AUD-007 — Неверный формат Telegram custom_title

```
ID:        AUD-007
Дата:      2026-07-02
Статус:    исправлен (заменён AUD-008)
Приоритет: high
Описание:  build_admin_title генерировал формат «Воин | Ник» вместо нужного.
           MEMBER не получал custom_title. В setrole.py game_nick не передавался.
Решение:   Переписан build_admin_title; MEMBER получает promote + custom_title;
           добавлена передача game_nick во всех call sites.
Файлы:    bot/utils/sync_title.py, nick.py, setrole.py, group_nick.py, members.py
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
Описание:  API Server падал с "Cannot find package 'esbuild'".
Причина:   node_modules отсутствовали в новой среде.
Решение:   pnpm install --no-frozen-lockfile
```

---

## AUD-003 — vite: not found при запуске Component Preview Server

```
ID:        AUD-003
Дата:      2026-07-02
Статус:    исправлен
Приоритет: high
Описание:  Mockup sandbox падал с "sh: 1: vite: not found".
Причина:   node_modules отсутствовали.
Решение:   pnpm install
```

---

## AUD-004 — AttributeError: BTN.GUIDES при импорте content.py

```
ID:        AUD-004
Дата:      2026-07-02
Статус:    исправлен
Приоритет: critical
Описание:  Бот падал при старте — константы BTN.GUIDES/SCREENSHOTS/MEMES удалены.
Решение:   Константы восстановлены в BTN.
Файлы:     bot/keyboards/main_menu.py
```

---

## AUD-005 — Дублирующиеся зависимости в requirements.txt

```
ID:        AUD-005
Дата:      2026-07-02
Статус:    исправлен
Приоритет: low
Решение:   Дубликаты удалены.
```

---

## AUD-006 — Дублирующаяся константа _SUPERUSER в members.py

```
ID:        AUD-006
Дата:      2026-07-02
Статус:    исправлен
Приоритет: low
Решение:   Локальная константа удалена.
```

---

## AUD-009 — clean_absent: сбой API трактовался как подтверждённое отсутствие

```
ID:        AUD-009
Дата:      2026-07-02
Статус:    исправлен
Приоритет: high
Описание:  В cb_mem_clean_absent_ok после TelegramRetryAfter + повторной ошибки
           код устанавливал member = None и продолжал удалять пользователя из БД,
           трактуя сбой проверки как подтверждённое отсутствие. При нестабильном API
           могла произойти массовая случайная очистка действующих участников.
Причина:   Отсутствие явного флага is_absent; ветка except устанавливала None
           вместо пропуска участника.
Решение:   Введён флаг is_absent = False. Удаление происходит только при
           is_absent = True, который устанавливается исключительно при подтверждённом
           статусе left/kicked или явном TelegramBadRequest "user not participant".
           Любой неоднозначный сбой API → skipped, участник не трогается.
Файлы:     bot/handlers/members.py (cb_mem_clean_absent_ok)
```

---

## ОЖИДАЕМЫЕ (НЕ ДЕФЕКТЫ)

- `TelegramBadRequest: chat not found` в логах после smoke-тестов —
  нормально: фейковые chat_id не могут получать ответы.
  (см. `.agents/memory/smoke-test-errors.md`)
