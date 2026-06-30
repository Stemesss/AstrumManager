# Контракты и инварианты

## 1. Контракты запуска

### 1.1 Основной entrypoint

- Основной запуск бота выполняется через `main.py`.
- Любые будущие изменения должны сохранять рабочий путь `python3 main.py`.

### 1.2 Контракт выбора режима

- Если найден публичный URL, бот обязан работать через webhook.
- Если публичный URL не найден, бот обязан уметь работать через polling.

Это поведение завязано на `resolve_public_host()` и не должно ломаться без отдельного migration-плана.

## 2. Контракт webhook proxy

Путь webhook жёстко согласован между компонентами:

- Python: `main.py` использует `/api/telegram/webhook`
- Node.js: `artifacts/api-server/src/routes/telegram.ts` проксирует `/api/telegram/*`

Следствие:

- нельзя менять путь только в одном месте;
- нельзя подключать JSON body parser к `/api/telegram`, иначе proxy может сломать передачу тела запроса в aiogram.

## 3. Контракт composition root

`build_dispatcher()` является центральной точкой сборки зависимостей.

Текущие обработчики и middleware рассчитывают на наличие в dispatcher context:

- `user_service`
- `news_service`
- `audit_service`
- `stats_service`
- `topic_service`
- `db`
- `owner_id`
- `group_chat_id`
- `bot_username`
- `bot_start_time`

Это нельзя менять фрагментарно: удаление или переименование ключей ломает существующие хендлеры.

## 4. Контракт разделения чатов

Архитектура явно разделяет потоки:

- group/supergroup logic живёт в отдельных роутерах;
- private logic живёт внутри отдельного `Router()` с фильтром `F.chat.type == "private"`.

Нельзя смешивать эти потоки без пересмотра:

- порядка middleware;
- регистрации FSM;
- ожиданий group-only и private-only хендлеров.

## 5. Контракт NickGate

`NickGateMiddleware` применяется только к приватным сообщениям после chat filtering.

Текущее поведение:

- пользователь без ника ограничивается до завершения настройки профиля;
- onboarding через `NickSetup` остаётся доступным;
- команды отмены и ранние flow-роутеры должны продолжать срабатывать в приоритетном порядке.

Из этого следует, что порядок private routers и место подключения NickGate — чувствительная часть архитектуры.

## 6. Контракт SQLite schema

Текущая бизнес-логика опирается на SQLite и таблицы из `bot/database/db.py`.

Ломать нельзя:

- названия таблиц;
- поля, которые уже читают сервисы и хендлеры;
- встроенные runtime-миграции в `connect()`;
- семантику `content_type` в таблице `news`;
- хранение форумных тем в `forum_topics`.

Отдельно:

- `TopicService` опирается на `forum_topics`;
- `StatsService` опирается одновременно на `news`, `audit_log` и `users`;
- `complaints` обслуживаются напрямую через `Database` в `handlers/complaints.py`.

## 7. Контракт topic subsystem

Подсистема тем централизована:

- реестр тем находится в `bot/models/topic.py`;
- runtime-операции над темами находятся в `bot/services/topic_service.py`.

Нельзя ломать:

- `TOPIC_REGISTRY` как центральный источник системных тем;
- связь `topic key -> Telegram thread`;
- startup seed/check тем;
- публикацию по ключу темы через `TopicService.publish(...)`.

## 8. Контракт контента

Контентные разделы (`news`, `events`, `guides`, `screenshots`, `memes`, `rules`) используют смешанную модель:

- сами записи лежат в таблице `news` с разным `content_type`;
- действия пользователей дополнительно пишутся в `audit_log`;
- публикация в Telegram может идти через `TopicService`.

Нельзя ломать:

- mapping `content_type`;
- журналирование `AuditAction`;
- текущие названия ключей в `_TYPES` у `handlers/publish.py`.

## 9. Контракт ролей и прав

Текущая модель ролей находится в `bot/models/user.py`:

- `Лидер`
- `Старейшина`
- `Дитя клана`
- `Участник`

`UserService.is_admin()` трактует административные права через `UserRole.admin_roles()`.

Нельзя без отдельной миграции менять:

- строковые значения ролей;
- правило определения admin roles;
- ожидания хендлеров, которые фильтруют админские действия по текущей модели ролей.

## 10. Что нельзя ломать на следующих этапах

1. Запуск `python3 main.py`.
2. Двухрежимный запуск webhook/polling.
3. Текущие таблицы SQLite и их поля.
4. Dispatcher injection через `dp[...]`.
5. Разделение group/private routing.
6. Nick onboarding flow.
7. Централизованный registry форумных тем.
8. Proxy-контракт `/api/telegram/*` между Express и Python.
9. Существующие `AuditAction` и `content_type`.
10. Отсутствие изменений в бизнес-логике на документационном этапе.
