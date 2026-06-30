# -*- coding: utf-8 -*-
"""Health-check и маршруты observability."""
import datetime as dt
import logging
from collections.abc import Callable

from aiohttp import web

from bot.config import FeatureFlags, ObservabilityConfig
from bot.database.db import Database
from bot.observability.metrics import MetricsRegistry

logger = logging.getLogger(__name__)


def _serialize_metrics_snapshot(snapshot: dict[str, object]) -> dict[str, object]:
    started_at = snapshot.get("started_at")
    last_update_at = snapshot.get("last_update_at")
    return {
        "mode": snapshot.get("mode"),
        "started_at": started_at.isoformat() if isinstance(started_at, dt.datetime) else None,
        "last_update_at": last_update_at.isoformat() if isinstance(last_update_at, dt.datetime) else None,
        "counters": snapshot.get("counters", {}),
        "update_types": snapshot.get("update_types", {}),
    }


class HealthService:
    """Проверки состояния рантайма."""

    def __init__(
        self,
        db: Database,
        metrics: MetricsRegistry,
        started_at_provider: Callable[[], dt.datetime | None],
    ) -> None:
        self._db = db
        self._metrics = metrics
        self._started_at_provider = started_at_provider

    async def snapshot(self) -> tuple[dict[str, object], int]:
        started_at = self._started_at_provider()
        database_ok = await self._db.ping()
        now = dt.datetime.now(dt.timezone.utc)
        uptime_seconds = 0
        if started_at is not None:
            uptime_seconds = max(0, int((now - started_at).total_seconds()))

        payload = {
            "status": "ok" if database_ok else "degraded",
            "service": "astrum-bot",
            "checks": {
                "database": "ok" if database_ok else "error",
            },
            "runtime": {
                "uptime_seconds": uptime_seconds,
                "started_at": started_at.isoformat() if started_at else None,
                "metrics": _serialize_metrics_snapshot(self._metrics.snapshot()),
            },
        }
        return payload, 200 if database_ok else 503


def _join_path(prefix: str, suffix: str) -> str:
    prefix = prefix.strip().rstrip("/")
    suffix = suffix.strip()
    if not suffix or suffix == "/":
        return prefix or "/"
    suffix = suffix if suffix.startswith("/") else f"/{suffix}"
    if not prefix:
        return suffix
    return f"{prefix}{suffix}"


def register_observability_routes(
    app: web.Application,
    features: FeatureFlags,
    observability: ObservabilityConfig,
    health_service: HealthService,
    metrics: MetricsRegistry,
) -> list[str]:
    """Регистрирует observability endpoints и возвращает список путей."""
    routes: list[str] = []

    if features.healthcheck:
        path = _join_path(observability.path_prefix, "/healthz")

        async def health_handler(_request: web.Request) -> web.Response:
            payload, status = await health_service.snapshot()
            return web.json_response(payload, status=status)

        app.router.add_get(path, health_handler)
        routes.append(path)

    if features.metrics:
        path = _join_path(observability.path_prefix, "/metrics")

        async def metrics_handler(_request: web.Request) -> web.Response:
            return web.Response(
                text=metrics.render_prometheus(),
                content_type="text/plain",
            )

        app.router.add_get(path, metrics_handler)
        routes.append(path)

    return routes


class ObservabilityServer:
    """Отдельный HTTP-сервер observability для polling-режима."""

    def __init__(
        self,
        features: FeatureFlags,
        observability: ObservabilityConfig,
        health_service: HealthService,
        metrics: MetricsRegistry,
    ) -> None:
        self._features = features
        self._observability = observability
        self._health_service = health_service
        self._metrics = metrics
        self._runner: web.AppRunner | None = None
        self._paths: list[str] = []

    async def start(self) -> list[str]:
        if not self._features.observability:
            return []
        app = web.Application()
        paths = register_observability_routes(
            app=app,
            features=self._features,
            observability=self._observability,
            health_service=self._health_service,
            metrics=self._metrics,
        )
        if not paths:
            return []
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(
            self._runner,
            host=self._observability.host,
            port=self._observability.port,
        )
        await site.start()
        self._paths = paths
        logger.info(
            "Observability-сервер запущен на %s:%s (%s)",
            self._observability.host,
            self._observability.port,
            ", ".join(paths),
        )
        return paths

    async def stop(self) -> None:
        if self._runner is None:
            return
        await self._runner.cleanup()
        self._runner = None
        self._paths = []
