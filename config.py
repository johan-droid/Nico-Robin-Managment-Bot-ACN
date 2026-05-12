from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from sqlalchemy.engine import make_url

_INT_TUPLE_FIELDS = {
    "sudo_users",
    "commander_ids",
    "allowed_group_ids",
    "purge_channel_ids",
}


class _CommaSeparatedIntTupleMixin:
    @staticmethod
    def _parse_int_tuple(value: Any) -> tuple[int, ...]:
        if value in (None, "", ()):
            return ()
        if isinstance(value, str):
            return tuple(int(part.strip()) for part in value.split(",") if part.strip())
        if isinstance(value, int):
            return (value,)
        if isinstance(value, list | tuple | set):
            return tuple(int(part) for part in value)
        raise TypeError(
            "Value must be a comma-separated string or sequence of integers"
        )

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        if field_name in _INT_TUPLE_FIELDS:
            return self._parse_int_tuple(value)
        # Fallback to the next class in MRO (e.g., EnvSettingsSource)
        # We use getattr to satisfy the linter if the base is not explicitly defined in the mixin
        prepare = getattr(super(), "prepare_field_value", None)
        if prepare:
            return prepare(field_name, field, value, value_is_complex)
        return value


class _CommaSeparatedIntTupleEnvSource(_CommaSeparatedIntTupleMixin, EnvSettingsSource):
    pass


class _CommaSeparatedIntTupleDotEnvSource(
    _CommaSeparatedIntTupleMixin,
    DotEnvSettingsSource,
):
    pass


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        config = settings_cls.model_config
        env_source = _CommaSeparatedIntTupleEnvSource(
            settings_cls,
            case_sensitive=config.get("case_sensitive"),
            env_prefix=config.get("env_prefix"),
            env_nested_delimiter=config.get("env_nested_delimiter"),
            env_ignore_empty=config.get("env_ignore_empty"),
            env_parse_none_str=config.get("env_parse_none_str"),
        )
        dotenv_source = _CommaSeparatedIntTupleDotEnvSource(
            settings_cls,
            env_file=config.get("env_file"),
            env_file_encoding=config.get("env_file_encoding"),
            case_sensitive=config.get("case_sensitive"),
            env_prefix=config.get("env_prefix"),
            env_nested_delimiter=config.get("env_nested_delimiter"),
            env_ignore_empty=config.get("env_ignore_empty"),
            env_parse_none_str=config.get("env_parse_none_str"),
        )
        return init_settings, env_source, dotenv_source, file_secret_settings

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str = Field(default="", alias="BOT_TOKEN")
    webhook_url: str = Field(default="", alias="WEBHOOK_URL")
    webhook_secret: str = Field(default="", alias="WEBHOOK_SECRET")
    port: int = Field(default=8000, alias="PORT")

    # WebSocket Configuration
    websocket_enabled: bool = Field(default=True, alias="WEBSOCKET_ENABLED")
    websocket_port: int = Field(default=8001, alias="WEBSOCKET_PORT")
    websocket_cors_origin: str = Field(default="*", alias="WEBSOCKET_CORS_ORIGIN")
    websocket_ping_interval: int = Field(default=25, alias="WEBSOCKET_PING_INTERVAL")
    websocket_ping_timeout: int = Field(default=5, alias="WEBSOCKET_PING_TIMEOUT")

    # Real-time Events Configuration
    realtime_events_enabled: bool = Field(default=True, alias="REALTIME_EVENTS_ENABLED")
    event_batch_size: int = Field(default=100, alias="EVENT_BATCH_SIZE")
    event_retention_hours: int = Field(default=24, alias="EVENT_RETENTION_HOURS")

    sudo_users: tuple[int, ...] = Field(default=(), alias="SUDO_USERS")

    # ACN Leadership IDs
    captain_id: int = Field(default=0, alias="CAPTAIN_ID")
    commander_ids: tuple[int, ...] = Field(default=(), alias="COMMANDER_IDS")

    # Group/Channel Restrictions
    allowed_group_ids: tuple[int, ...] = Field(default=(), alias="ALLOWED_GROUP_IDS")
    purge_channel_ids: tuple[int, ...] = Field(default=(), alias="PURGE_CHANNEL_IDS")

    # ── Security Configuration ──
    metrics_api_key: str = Field(default="", alias="METRICS_API_KEY")

    # Rate Limiting (requests per minute)
    rate_limit_user: int = Field(default=20, alias="RATE_LIMIT_USER")
    rate_limit_group: int = Field(default=60, alias="RATE_LIMIT_GROUP")
    rate_limit_global: int = Field(default=300, alias="RATE_LIMIT_GLOBAL")
    rate_limit_cooldown: int = Field(default=30, alias="RATE_LIMIT_COOLDOWN")
    rate_limit_ban_threshold: int = Field(default=5, alias="RATE_LIMIT_BAN_THRESHOLD")

    # Database Pool Hardening
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=5, alias="DB_MAX_OVERFLOW")
    db_query_timeout: int = Field(default=10, alias="DB_QUERY_TIMEOUT")
    db_pool_recycle: int = Field(default=1800, alias="DB_POOL_RECYCLE")
    db_ssl_required: bool = Field(default=False, alias="DB_SSL_REQUIRED")

    database_url: str = Field(
        default="postgresql+asyncpg://robin:password@localhost:5432/robin_db",
        alias="DATABASE_URL",
    )

    # Celery Configuration
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0", alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND"
    )
    llm_provider: Literal["disabled", "openai", "traditional_ml"] = Field(
        default="disabled",
        alias="LLM_PROVIDER",
    )
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_moderation_model: str = Field(
        default="gpt-4o-mini",
        alias="OPENAI_MODERATION_MODEL",
    )
    ai_moderation_enabled: bool = Field(default=False, alias="AI_MODERATION_ENABLED")
    ai_score_threshold: float = Field(default=0.75, alias="AI_SCORE_THRESHOLD")

    log_channel_id: int | None = Field(default=None, alias="LOG_CHANNEL_ID")

    bot_name: str = Field(default="Nico Robin", alias="BOT_NAME")
    default_locale: str = Field(default="en", alias="DEFAULT_LOCALE")
    default_prefix: str = Field(default="/", alias="DEFAULT_PREFIX")
    environment: Literal["local", "test", "production"] = Field(
        default="local",
        alias="ENVIRONMENT",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )

    @field_validator(
        "sudo_users",
        "commander_ids",
        "allowed_group_ids",
        "purge_channel_ids",
        mode="before",
    )
    @classmethod
    def parse_int_tuple(cls, value: object) -> tuple[int, ...]:
        if value in (None, "", ()):
            return ()
        if isinstance(value, str):
            return tuple(int(part.strip()) for part in value.split(",") if part.strip())
        if isinstance(value, int):
            return (value,)
        if isinstance(value, list | tuple | set):
            return tuple(int(part) for part in value)
        raise TypeError(
            "Value must be a comma-separated string or sequence of integers"
        )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("DATABASE_URL must be a string")

        # Strip whitespace and handle postgres:// to postgresql:// conversion
        url = value.strip()
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)

        # Ensure it has the asyncpg driver for internal use if not already specified
        # but keep the base URL clean for the sync property
        return url

    @property
    def async_database_url(self) -> str:
        """SQLAlchemy async URL without libpq-only query parameters."""
        url = make_url(self.database_url)

        # Inject asyncpg driver if missing
        drivername = url.drivername
        if drivername == "postgresql":
            drivername = "postgresql+asyncpg"
        elif not drivername.endswith("+asyncpg"):
            drivername = f"{drivername}+asyncpg"

        query = dict(url.query)
        # Remove libpq-only parameters that asyncpg doesn't support
        query.pop("sslmode", None)
        query.pop("channel_binding", None)

        return url.set(drivername=drivername, query=query).render_as_string(
            hide_password=False
        )

    @property
    def async_database_ssl_required(self) -> bool:
        """Whether the async driver should connect over SSL."""
        url = make_url(self.database_url)
        sslmode = url.query.get("sslmode")

        return (
            self.db_ssl_required
            or self.environment == "production"
            or sslmode in {"require", "verify-ca", "verify-full"}
            or (
                url.host is not None and "neon.tech" in url.host
            )  # Neon always requires SSL
        )

    @property
    def sync_database_url(self) -> str:
        """SQLAlchemy sync URL for Alembic migrations."""
        url = make_url(self.database_url)
        drivername = url.drivername.replace("+asyncpg", "")
        return url.set(drivername=drivername).render_as_string(hide_password=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
