# -*- coding: utf-8 -*-
"""In-memory метрики для платформенных проверок."""
import datetime as dt
from collections import Counter
from threading import Lock


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


class MetricsRegistry:
    """Простой in-memory реестр счётчиков."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Counter[str] = Counter()
        self._update_types: Counter[str] = Counter()
        self._started_at: dt.datetime | None = None
        self._last_update_at: dt.datetime | None = None
        self._mode: str | None = None

    def mark_startup(self, mode: str) -> None:
        now = dt.datetime.now(dt.timezone.utc)
        with self._lock:
            self._started_at = now
            self._mode = mode
            self._counters["bot_startups_total"] += 1

    def mark_shutdown(self) -> None:
        with self._lock:
            self._counters["bot_shutdowns_total"] += 1

    def record_update(self, event_type: str) -> None:
        now = dt.datetime.now(dt.timezone.utc)
        with self._lock:
            self._last_update_at = now
            self._counters["bot_updates_total"] += 1
            self._update_types[event_type] += 1

    def record_error(self) -> None:
        with self._lock:
            self._counters["bot_errors_total"] += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "mode": self._mode,
                "started_at": self._started_at,
                "last_update_at": self._last_update_at,
                "counters": dict(self._counters),
                "update_types": dict(self._update_types),
            }

    def render_prometheus(self) -> str:
        snapshot = self.snapshot()
        counters = snapshot["counters"]
        update_types = snapshot["update_types"]
        started_at = snapshot["started_at"]
        last_update_at = snapshot["last_update_at"]
        mode = snapshot["mode"]

        lines = [
            "# HELP astrum_bot_startups_total Количество запусков бота",
            "# TYPE astrum_bot_startups_total counter",
            f"astrum_bot_startups_total {counters.get('bot_startups_total', 0)}",
            "# HELP astrum_bot_shutdowns_total Количество остановок бота",
            "# TYPE astrum_bot_shutdowns_total counter",
            f"astrum_bot_shutdowns_total {counters.get('bot_shutdowns_total', 0)}",
            "# HELP astrum_bot_updates_total Количество обработанных обновлений Telegram",
            "# TYPE astrum_bot_updates_total counter",
            f"astrum_bot_updates_total {counters.get('bot_updates_total', 0)}",
            "# HELP astrum_bot_errors_total Количество ошибок в middleware observability",
            "# TYPE astrum_bot_errors_total counter",
            f"astrum_bot_errors_total {counters.get('bot_errors_total', 0)}",
            "# HELP astrum_bot_update_events_total Количество обновлений по типам событий",
            "# TYPE astrum_bot_update_events_total counter",
        ]

        for event_type, count in sorted(update_types.items()):
            lines.append(
                f'astrum_bot_update_events_total{{event_type="{_escape_label(event_type)}"}} {count}'
            )

        lines.extend(
            [
                "# HELP astrum_bot_started_at_timestamp Время последнего старта бота (unix timestamp)",
                "# TYPE astrum_bot_started_at_timestamp gauge",
                f"astrum_bot_started_at_timestamp {started_at.timestamp() if started_at else 0}",
                "# HELP astrum_bot_last_update_timestamp Время последнего обновления (unix timestamp)",
                "# TYPE astrum_bot_last_update_timestamp gauge",
                f"astrum_bot_last_update_timestamp {last_update_at.timestamp() if last_update_at else 0}",
                "# HELP astrum_bot_runtime_mode Текущий режим запуска бота",
                "# TYPE astrum_bot_runtime_mode gauge",
            ]
        )

        for candidate in ("polling", "webhook"):
            value = 1 if mode == candidate else 0
            lines.append(f'astrum_bot_runtime_mode{{mode="{candidate}"}} {value}')

        return "\n".join(lines) + "\n"
