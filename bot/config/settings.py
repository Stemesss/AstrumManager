# -*- coding: utf-8 -*-
"""Загрузка конфигурации из переменных окружения."""
import os
from dataclasses import dataclass, field

DEFAULT_WEBHOOK_PATH = "/api/telegram/webhook"


@dataclass(frozen=True)
class FeatureFlags:
    """Feature flags платформенных возможностей."""

    observability: bool = False
    healthcheck: bool = False
    metrics: bool = False


@dataclass(frozen=True)
class RuntimeConfig:
    """Параметры запуска бота."""

    public_host: str | None = None
    webhook_path: str = DEFAULT_WEBHOOK_PATH
    port: int = 6000
    log_level: str = "INFO"


@dataclass(frozen=True)
class ObservabilityConfig:
    """Параметры observability-слоя."""

    host: str = "0.0.0.0"
    port: int = 6000
    path_prefix: str = ""


@dataclass
class Config:
    bot_token: str
    db_path: str = field(default="data/astrum.db")
    owner_id: int | None = field(default=None)
    group_chat_id: int = field(default=-1004463841801)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)


def _parse_optional_int(name: str, default: int | None = None) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} должен быть числом, получено: {raw!r}") from exc


def _parse_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} должен быть булевым значением, получено: {raw!r}")


def _resolve_public_host() -> str | None:
    override = os.getenv("WEBHOOK_BASE_URL", "").strip()
    if override:
        return override.rstrip("/")

    replit = os.getenv("REPLIT_DOMAINS", "").split(",")[0].strip()
    if replit:
        return f"https://{replit}"

    railway = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if railway:
        return f"https://{railway}"

    return None


def load_config() -> Config:
    """Загружает конфигурацию из переменных окружения."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(
            "Переменная окружения TELEGRAM_BOT_TOKEN не задана. "
            "Получите токен у @BotFather и добавьте его в секреты проекта."
        )

    db_path = os.getenv("DB_PATH", "data/astrum.db")
    owner_id = _parse_optional_int("BOT_OWNER_ID")
    group_chat_id = _parse_optional_int("GROUP_CHAT_ID", -1004463841801)
    runtime_port = _parse_optional_int("PORT")
    if runtime_port is None:
        runtime_port = _parse_optional_int("WEBHOOK_PORT", 6000)
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"

    features = FeatureFlags(
        observability=_parse_bool("FEATURE_OBSERVABILITY", False),
        healthcheck=_parse_bool("FEATURE_HEALTHCHECK", False),
        metrics=_parse_bool("FEATURE_METRICS", False),
    )
    runtime = RuntimeConfig(
        public_host=_resolve_public_host(),
        webhook_path=os.getenv("WEBHOOK_PATH", DEFAULT_WEBHOOK_PATH).strip() or DEFAULT_WEBHOOK_PATH,
        port=runtime_port,
        log_level=log_level,
    )
    observability = ObservabilityConfig(
        host=os.getenv("OBSERVABILITY_HOST", "0.0.0.0").strip() or "0.0.0.0",
        port=_parse_optional_int("OBSERVABILITY_PORT", runtime.port) or runtime.port,
        path_prefix=os.getenv("OBSERVABILITY_PATH_PREFIX", "").strip().rstrip("/"),
    )

    return Config(
        bot_token=token,
        db_path=db_path,
        owner_id=owner_id,
        group_chat_id=group_chat_id,
        runtime=runtime,
        features=features,
        observability=observability,
    )
