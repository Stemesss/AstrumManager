---
name: Dev rules
description: Правила разработки проекта AstrumManager — обязательны к исполнению
---

# Правила разработки AstrumManager

## 1. Общие правила

- Не изменять код без явного задания от пользователя.
- Не создавать новые файлы без необходимости.
- Всегда сохранять существующую структуру модулей.
- Не использовать глобальные переменные — только DI через `dp["name"]`.
- Комментарии в коде — на русском языке (в соответствии с проектом).

## 2. Архитектурные правила

### Webhook
- На Replit и Railway — только webhook-режим.
- Polling запрещён (Replit блокирует исходящие на api.telegram.org).
- Авто-детекция: `WEBHOOK_BASE_URL` → `REPLIT_DOMAINS` → `RAILWAY_PUBLIC_DOMAIN` → polling (только local).

### Два процесса
- Python-бот (aiohttp): порт 6000, только для внутренних запросов.
- Node.js Express: порт 8080, публичный прокси.
- Express ДОЛЖЕН пропускать `/api/telegram` без `json()` парсинга тела.

### База данных
- Только SQLite через aiosqlite.
- WAL-режим обязателен (`PRAGMA journal_mode=WAL`).
- Все операции — через `Database`-класс (`bot/database/db.py`).
- Перед сбросом сезона — создать бэкап (`db.create_backup()`).

## 3. Правила по коду

### Инъекция зависимостей
```python
# В build_dispatcher() в main.py:
dp["user_service"] = UserService(db)

# В handler:
async def handler(message: Message, user_service: UserService) -> None:
    ...
```
Список инъектируемых объектов: `user_service`, `audit_service`, `stats_service`,
`news_service`, `topic_service`, `db`, `group_chat_id`, `owner_id`.

### Ники пользователей
- `game_nick` в БД хранит ТОЛЬКО имя (например: "Вадим").
- Полный ник = `build_full_nick(name, role)` → "🌟 Рекрут｜Вадим".
- Разделитель: `｜` (U+FF5C fullwidth vertical bar, не обычный `|`).
- Нельзя хранить полный ник в БД — он вычисляется на лету.

### Роли
```
LEADER     → "👑 Лидер"
ELDER      → "🛡️ Старейшина"
CLAN_CHILD → "⚔️ Воин"
MEMBER     → "🌟 Рекрут"
```

### Защита пользователей
- Нельзя удалить суперпользователя (owner_id = 8490615925).
- Нельзя удалить себя.
- Нельзя удалить пользователя с ролью LEADER.

### Очки активности
Вычисляются on-the-fly из `audit_log` (не хранятся в отдельной таблице):
```
news_create       = 5
guide_create      = 10
screenshot_upload = 2
event_create      = 8
```

## 4. Порядок регистрации роутеров

```python
# В main.py, private router:
cancel → common → setrole → nick → audit → news → publish → topics →
icons → members → content → complaints → rules → admin → stats →
statistics → menu → echo
```

Порядок важен — более специфичные обработчики должны идти раньше.

## 5. Правила памяти агента

- После каждого задания — обновить файлы памяти (не ждать команды).
- Не сохранять в память: секреты, пути к файлам, имена функций, номера строк.
- Сохранять в память: архитектурные решения, нетривиальные ограничения, паттерны.
- MEMORY.md — только индекс (одна строка на файл).
- topic-файлы — детальное описание.

## 6. Правила Git

- git commit/add заблокированы в main agent — коммит создаётся автоматически (checkpoint).
- git push без force-флагов — разрешён.
- Сообщение коммита — осмысленное, на английском.
- Все файлы памяти (.agents/memory/) должны попадать в Git.
- AGENT_START.md и PROJECT_HISTORY.md — тоже в Git.

## 7. Правила тестирования

- После каждого изменения — проверить логи воркфлоу.
- Ошибка "TelegramBadRequest: chat not found" после smoke-тестов — ожидаема, не дефект.
- Реальное тестирование — отправкой сообщений боту.

## 8. Запрещено

- Использовать polling на Replit/Railway.
- Хранить полный ник в БД.
- Использовать обычный `|` вместо `｜` (U+FF5C).
- Изменять `owner_id` (8490615925) в коде.
- Добавлять `json()` middleware для `/api/telegram` путей в Express.
- Создавать глобальные синглтоны сервисов.
