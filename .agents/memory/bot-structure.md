---
name: Bot module structure
description: Canonical directory layout for the AstrumManager bot after all refactors
---

## Layout (under `bot/`)

```
bot/
  config/          — settings.py (Config dataclass, load_config)
  models/          — user.py: UserRole + User; audit.py: AuditAction constants + CATEGORY_ACTIONS;
                     stats.py: UserActivity/NewsStats/ContentStats/ClanGrowth; topic.py: TOPIC_REGISTRY
  database/        — db.py: Database class (aiosqlite, WAL); tables: users, audit_log, news,
                     forum_topics, publication_attachments, complaints
  services/        — UserService, AuditService, StatsService, NewsService, TopicService
  keyboards/       — one file per section; admin_panel.py: AdminBtn + ADMIN_PANEL_KB
  utils/           — roles.py, sync_title.py, profile.py, text.py
  states/          — one file per FSM section; members.py: MemberDelete
  handlers/        — one file per section; registered in main.py
  middlewares/     — logging.py: LoggingMiddleware
```

## Router registration order in main.py (private router)
cancel → common → setrole → nick → audit → news → publish → topics → icons →
members → content → complaints → rules → admin → stats → statistics → menu → echo

## Key architectural facts

- **Scores** are computed on-the-fly from audit_log (no separate points table).
  Formula: news_create=5, guide_create=10, screenshot_upload=2, event_create=8.
- **Season reset** = DELETE FROM audit_log (keeps users, forum_topics, news, complaints).
  Backup is created first via `db.create_backup()` → `data/backups/astrum_{ts}.db`.
- **Members section** now has a submenu (mem:menu) before the list.
  Entry: AdminBtn.MEMBERS → members menu → list / delete flow / season.
- **Delete member** protection: can't delete superuser (8490615925), self, or UserRole.LEADER.
- **MemberDelete.waiting_search** FSM state handles text search in delete flow.

## Dependency injection
`dp["user_service"] = UserService(db)` in `build_dispatcher()`; handlers declare typed kwargs.
Also injected: audit_service, stats_service, news_service, topic_service, group_chat_id, db, owner_id.

**Why:** Single source of truth for each concern; handlers stay thin.
