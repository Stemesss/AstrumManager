---
name: Change log
description: Журнал изменений — обновляется после каждого выполненного задания
---

# Журнал изменений

## [1.2.2] — 2026-07-02 — Полировка меню «Участники»

### Проверено (без изменений — уже соответствовало требованиям)
- Меню «Администрация → Участники» уже не содержало кнопки ⚙️ Настройки —
  она была убрана ранее (v1.1.0). Кнопка «🗑️ Удалить участника» уже
  присутствовала (`members_menu_kb`) и полный цикл удаления уже был
  реализован: список → карточка с подтверждением → удаление из БД
  (`user_service.delete_member` → `db.delete_user`, стирает пользователя,
  записи `audit_log` и `complaints`) → обновление списка → запись в журнал
  аудита (`AuditAction.MEMBER_DELETE`).

### Добавлено
- `bot/keyboards/members.py` — новый класс `MemberViewBtn` и функции
  `view_list_kb` / `view_card_kb` — клавиатуры раздела просмотра участников
  для главного меню (без кнопок роли/статистики/удаления).
- `bot/handlers/members.py` — обработчики `memv:list:{page}`,
  `memv:card:{uid}:{page}`, `memv:noop`, `memv:close` и новый обработчик
  `F.text == BTN.MEMBERS`, показывающий карточки участников с той же
  сортировкой и пагинацией, что и в админ-разделе, но полностью в режиме
  просмотра (нет кнопок изменения роли, статистики, удаления).

### Изменено
- `bot/keyboards/members.py` — `_pagination_rows` принимает параметр `noop`
  (по умолчанию `MemberBtn.NOOP`), чтобы отдельный callback-неймспейс
  `memv:` для просмотра не пересекался с админским `mem:`.
- `bot/handlers/menu.py` — обработчик `F.text == BTN.MEMBERS` (плоский
  текстовый список) удалён и заменён карточным просмотром в
  `bot/handlers/members.py`; удалён более не используемый импорт
  `role_label`.

## [1.2.1] — 2026-07-02 — Финальная полировка (полный аудит)

### Исправлено (критично)
- `bot/keyboards/main_menu.py` — восстановлены константы BTN.GUIDES,
  BTN.SCREENSHOTS, BTN.MEMES (удалены по ошибке в v1.2.0 вместе с кнопками
  из MAIN_KEYBOARD; bot/handlers/content.py от них зависел как от ключей
  конфигурации разделов). Без этой правки бот не запускался (AttributeError
  при импорте). См. AUD-004.

### Исправлено (мелкое)
- Удалены неиспользуемые импорты (pyflakes) в 12 файлах: admin.py, audit.py,
  content.py, news.py, rules.py, icons.py, members.py, menu.py, publish.py,
  topics.py, bot/keyboards/members.py, bot/models/topic.py.
- Исправлены 3 f-строки без плейсхолдеров: complaints.py, nick.py, content.py.
- `requirements.txt` — удалён дублирующийся блок зависимостей (AUD-005).
- `bot/handlers/members.py` — убрана дублирующая локальная константа
  `_SUPERUSER`, используется существующая `_SUPERUSER_ID` (AUD-006).

### Проверено (без изменений — код корректен)
- Все callback_data во всех клавиатурах имеют зарегистрированные обработчики.
- Все 21 роутер зарегистрированы в main.py, порядок соответствует правилам.
- FSM-состояния во всех states/*.py имеют обработчики и пути очистки/отмены.
- NickGateMiddleware не создаёт блокировок пользователей.
- SQL-запросы параметризованы, инъекций нет.

### Инфраструктура
- Переустановлены Python-зависимости (requirements.txt) и Node-зависимости
  (pnpm install) — окружение было пересоздано, node_modules/site-packages
  отсутствовали (аналогично AUD-001/002/003).

## [1.2.0] — 2026-07-02 — Полировка главного меню

### Удалено
- `bot/keyboards/main_menu.py` — кнопки «😂 Мемы», «📚 Гайды», «📸 Скриншоты» из BTN и из MAIN_KEYBOARD
- `bot/handlers/menu.py` — строки «Гайды», «Скриншоты», «Мемы» из текста справки

### Изменено
- `bot/keyboards/main_menu.py` — новая раскладка 5×2: Новости/События | Правила/Жалобы | Участники/Администрация | Журнал/Статистика | Профиль/Помощь

## [1.1.0] — 2026-07-02 — Полировка раздела «Участники»

### Изменено
- `bot/utils/roles.py` — ROLE_ORDER: LEADER→ELDER→CLAN_CHILD→MEMBER
- `bot/keyboards/members.py` — иконки ✪✦✧◇→👑🛡⭐👤; убрана кнопка ⚙️
- `bot/handlers/members.py` — иконки ✪✦✧◇→👑🛡⭐👤; фильтр game_nick в _show_list()

## [1.0.2] — 2026-07-02 — Безопасность webhook

### Добавлено
- `bot/config/settings.py` — поле webhook_secret (WEBHOOK_SECRET env или auto-generated)
- `main.py` — secret_token в set_webhook и SimpleRequestHandler

## [1.0.1] — 2026-07-02 — Git-скрипты

### Добавлено
- `scripts/push.sh`, `scripts/pull.sh`
