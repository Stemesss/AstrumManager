---
name: Menu button constant coupling
description: BTN class in bot/keyboards/main_menu.py is used as shared config keys across handlers, not just reply-keyboard labels — pruning a constant without checking usages crashes the bot at import time.
---

# Проблема

`BTN` (в `bot/keyboards/main_menu.py`) задумывался как "единственный источник истины"
для текста кнопок главного меню, но на практике его константы (`BTN.GUIDES`,
`BTN.SCREENSHOTS`, `BTN.MEMES` и т.п.) используются далеко за пределами самой
клавиатуры — например, как ключи в `_TYPES` конфиге `bot/handlers/content.py` и
как текстовые точки входа в `@router.message(F.text == BTN.X)`.

Когда в рамках полировки меню кнопку убрали из `MAIN_KEYBOARD`, соответствующую
константу удалили из класса `BTN` целиком — это привело к `AttributeError` при
импорте `bot.handlers.content` и полному падению бота при старте (ModuleNotFoundError
уровня приложения, а не просто "мёртвая кнопка").

**Why:** класс с константами в этом проекте выполняет двойную роль — визуальная
подпись кнопки И программный идентификатор раздела/конфига. Range-удаление
константы вместе с кнопкой ломает всех потребителей константы, даже если сама
кнопка больше не отображается пользователю.

**How to apply:** перед удалением любой константы из `BTN` (или аналогичных
классов-констант типа `AdminBtn`, `MemberBtn`) — грепать использование имени
константы по всему `bot/`, а не только по файлу клавиатуры. Если константа
используется как ключ конфигурации в handlers, но кнопку в разметке убрали —
оставить константу в классе (доступ через прямой ввод текста / другие точки
входа сохраняется), просто не добавлять её в `ReplyKeyboardMarkup`.
