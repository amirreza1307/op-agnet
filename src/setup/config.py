import os
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Sentinel value used as the default for credential fields that must come from
# the environment. The validator below raises if either field still equals this
# value at startup, so a missing env var fails loud instead of silently booting
# with weak built-in credentials.
_REQUIRED_SENTINEL = "<unset>"


class Config(BaseSettings):
    APP_ENV: str = "local"
    DEBUG: bool = True
    APP_NAME: str = "agent-graph-platform"
    BOOTSTRAP_FAIL_FAST: bool = False

    SENTRY_DSN: str = ""
    SENTRY_DEBUG_ENABLED: bool = False
    SENTRY_RELEASE: str = ""
    SENTRY_ENVIRONMENT: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 1
    SENTRY_PROFILES_SAMPLE_RATE: float = 1
    SENTRY_AUTO_SESSION_TRACKING: bool = False

    HTTP_TIMEOUT_IN_SECONDS: int = 30
    HTTP_RETRIES: int = 3

    # No safe default: must be supplied via MAIN_POSTGRES_USER / MAIN_POSTGRES_PASS
    # env vars. The validator below rejects the sentinel so a mis-deployed
    # environment fails loud instead of booting with weak credentials.
    MAIN_POSTGRES_USER: str = _REQUIRED_SENTINEL
    MAIN_POSTGRES_PASS: str = _REQUIRED_SENTINEL
    MAIN_POSTGRES_HOST: str = "localhost"
    MAIN_POSTGRES_PORT: str = "5432"
    MAIN_POSTGRES_DATABASE: str = "platform_agent"
    LOCAL_MAIN_POSTGRES_HOST: str = "localhost"
    MAIN_POSTGRES_TIMEOUT: int = 10000
    MAIN_POSTGRES_ACQUIRE_TIMEOUT_IN_SECONDS: int = 10
    # Recycle idle pool connections after 10 minutes. Set to 0 to disable
    # recycling (not recommended in production: stale connections survive
    # network blips and fail on next use).
    MAIN_POSTGRES_POOL_MAX_INACTIVE_CONNECTION_LIFETIME: int = 600
    MAIN_POSTGRES_CONNECTION_POOL_MIN_SIZE: int = 2
    MAIN_POSTGRES_CONNECTION_POOL_MAX_SIZE: int = 8

    PLATFORM_SCHEMA: str = "platform"
    VENDOR_SCHEMA: str = "vendor"
    ANALYTICS_SCHEMA: str = "analytics"
    ANALYTICS_RETENTION_DAYS: int = 180
    ANALYTICS_REFRESH_WINDOW_DAYS: int = 7

    AGNO_DB_SCHEMA: str = "agno"
    AGNO_DB_INIT_FAIL_FAST: bool = False
    AGNO_SESSION_TABLE: str = "agno_sessions"
    AGNO_MEMORY_TABLE: str = "agno_memories"
    AGNO_METRICS_TABLE: str = "agno_metrics"
    AGNO_EVAL_TABLE: str = "agno_eval_runs"
    AGNO_KNOWLEDGE_TABLE: str = "agno_knowledge"
    AGNO_TRACES_TABLE: str = "agno_traces"
    AGNO_SPANS_TABLE: str = "agno_spans"
    AGNO_VERSIONS_TABLE: str = "agno_schema_versions"
    AGNO_LEARNINGS_TABLE: str = "agno_learnings"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_TIMEOUT: int = 60
    OPENROUTER_PROXY: str = ""
    AGNO_MODEL: str = "openai/gpt-4o"
    OPENROUTER_TOOL_MODEL: str = "openai/gpt-4o-mini"
    AGNO_MEMORY_MODEL: str = "deepseek/deepseek-v4-flash"

    NUMBERLAND_ORDER_BASE_URL: str = "https://order.numberland.ir"
    NUMBERLAND_AUTH_BASE_URL: str = "https://auth.numberland.ir"
    NUMBERLAND_CLIENT_ID: str = ""
    NUMBERLAND_CLIENT_SECRET: str = ""
    NUMBERLAND_REQUEST_TIMEOUT_SECONDS: float = 20.0
    NUMBERLAND_TOKEN_REFRESH_SKEW_SECONDS: int = 30


    PLATFORM_CACHE_EAGER_LOAD: bool = True
    PLATFORM_MAX_GRAPH_DEPTH: int = 8
    PLATFORM_DEFAULT_HISTORY_RUNS: int = 12
    PLATFORM_DEFAULT_TOOL_CALL_LIMIT: int = 6
    PLATFORM_DEFAULT_SESSION_TABLE: str = "agno_sessions"
    PLATFORM_RUNTIME_CACHE_ENABLED: bool = True
    PLATFORM_ADMIN_MCP_HOST: str = "127.0.0.1"
    PLATFORM_ADMIN_MCP_PORT: int = 9015
    ADMIN_ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,https://vendor-insight.titanapp.dev,https://vendor-agent.basalam.com"
    ADMIN_SECRET_KEY: str = ""
    ADMIN_SECRET_HEADER_NAME: str = "X-Admin-Secret-Key"

    # Per-agent Telegram/Bale channels. Comma-separated Fernet keys allow
    # rotation: the first key encrypts and every configured key decrypts.
    CHANNEL_TOKEN_ENCRYPTION_KEY: str = ""
    CHANNEL_PUBLIC_BASE_URL: str = ""
    CHANNEL_ERROR_MESSAGE: str = (
        "متأسفانه هنگام پردازش پیام خطایی رخ داد. لطفاً دوباره تلاش کنید."
    )

    CACHE_TOOLS_TTL_SECONDS: int = 86400
    VENDOR_TOOLTIP_DEFAULT_TEXT: str = ""
    VENDOR_TOOLTIP_DEFAULT_DURATION_SECONDS: int = 30

    MCP_DEFAULT_TIMEOUT_SECONDS: int = 15
    MCP_ROOT_DIR: str = ""
    SKILLS_ROOT_DIR: str = ""
    CLICKHOUSE_HTTP_BASE_URL: str = ""
    CLICKHOUSE_HTTP_API_KEY: str = ""
    CLICKHOUSE_USE_PROXY: bool = False
    CLICKHOUSE_MODE: str = "http"
    CLICKHOUSE_NATIVE_HOST: str = ""
    CLICKHOUSE_NATIVE_PORT: int = 9440
    CLICKHOUSE_NATIVE_USER: str = ""
    CLICKHOUSE_NATIVE_PASSWORD: str = ""
    CLICKHOUSE_NATIVE_DATABASE: str = "OLAPBasalam"
    CLICKHOUSE_NATIVE_SECURE: bool = True
    CLICKHOUSE_KEYWORD_TABLE: str = "OLAPBasalam.search_product_keyword"
    CLICKHOUSE_KEYWORD_SOURCE: str = "table"
    CLICKHOUSE_S3_ACCESS_KEY: str = ""
    CLICKHOUSE_S3_SECRET_KEY: str = ""
    CLICKHOUSE_S3_IMPRESSION_KEYWORD_PATH_TEMPLATE: str = ""
    CLICKHOUSE_S3_CLICK_PRODUCT_KEYWORD_PATH_TEMPLATE: str = ""
    # ── Action impact measurement jobs ──────────────────────────────
    # How often the in-app scheduler ticks. Default 1h; impact measurements are
    # not time-sensitive and batch metrics are cheaper run hourly than every minute.
    IMPACT_TICK_SECONDS: int = 3600
    # Max SINGLE-mode measurements claimed per tick.
    IMPACT_BATCH_LIMIT: int = 50
    # Max entities pulled into ONE batch-mode query (global, no per-metric
    # override). Bounds query cost; remaining due rows wait for the next tick.
    IMPACT_BATCH_ENTITY_LIMIT: int = 500
    # TTL of the tick leader lock — must exceed a tick's worst-case duration.
    IMPACT_LOCK_TTL_SECONDS: int = 90
    # statement_timeout (ms) applied to every read-only metric query.
    IMPACT_STATEMENT_TIMEOUT_MS: int = 30000
    # A measurement stuck in CLAIMED longer than this (a worker crashed between
    # claim and result-write) is reset to PENDING at the start of a tick so it
    # gets re-processed. Must comfortably exceed one tick's worst-case runtime.
    IMPACT_CLAIM_RECLAIM_SECONDS: int = 3600
    # Master switch: disable the scheduler without removing wiring (e.g. local).
    IMPACT_SCHEDULER_ENABLED: bool = True

    ANALYTICS_SYNC_CHUNK_SIZE: int = 100
    ANALYTICS_SYNC_CLICKHOUSE_PAGE_SIZE: int = 25000
    ANALYTICS_SYNC_UPSERT_BUFFER_SIZE: int = 2000
    ANALYTICS_LEGEND_ENABLED: bool = False

    VENDOR_SUPPORT_TICKET_API_URL: str = "https://ticket-agent-2.titanapp.dev"
    VENDOR_AUTH_USER_API_URL: str = "https://services.basalam.com/web/v1/core/user"
    VENDOR_AUTH_REQUEST_TIMEOUT_SECONDS: int = 15
    VENDOR_AUTH_DEFAULT_ORIGIN: str = "https://basalam.com"
    VENDOR_AUTH_DEFAULT_REFERER: str = "https://basalam.com/"
    VENDOR_AUTH_DEFAULT_USER_AGENT: str = "Mozilla/5.0"

    VENDOR_PRODUCTS_API_BASE_URL: str = "https://core.basalam.com"
    VENDOR_PRODUCTS_REQUEST_TIMEOUT_SECONDS: int = 20

    PRODUCT_AUTO_EDIT_FIELDS: str = "title,description,preparation_day"
    # Minimum length (chars) the LLM-proposed title must satisfy. Leave empty
    # to drop the constraint from the prompt entirely.
    PRODUCT_TITLE_MIN_CHARS: int | None = None

    VENDOR_ORDERS_API_BASE_URL: str = "https://order-processing.basalam.com"
    VENDOR_ORDERS_REQUEST_TIMEOUT_SECONDS: int = 20

    UPLOADIO_BASE_URL: str = "https://uploadio.basalam.com"
    UPLOADIO_SECRET: str = ""

    # Basalam public API gateway. Used for endpoints the SDK does not yet
    # wrap (e.g. the Shipping free-shipping-rules routes under /v1/shipping).
    BASALAM_GATEWAY_BASE_URL: str = "https://openapi.basalam.com"
    BASALAM_GATEWAY_REQUEST_TIMEOUT_SECONDS: float = 20.0

    # Basalam voucher service. Hosts the coupon subsystems (store coupons under
    # /v2/coupon and shareable code coupons under /api_v1.0/coupon). NOT wrapped
    # by the SDK, so the manage_voucher tools call it directly over httpx with
    # the forwarded user bearer token.
    VOUCHER_BASE_URL: str = "https://voucher.basalam.com"
    VOUCHER_REQUEST_TIMEOUT_SECONDS: float = 20.0

    # Salam-Pay (سلام‌پی) BNPL credit-line service. NOT wrapped by the Basalam
    # SDK. Reads / the simulate preview / edits (PATCH) live on the bnpl host;
    # create lives on the gateway host (a different URL). Called via the typed
    # SalampaySDK (setup/sdks/salampay) with the forwarded user bearer token.
    SALAMPAY_BNPL_BASE_URL: str = "https://bnpl.basalam.com"
    SALAMPAY_CREATE_URL: str = (
        "https://salam-pay-api.basalam.com/gateway/bnpl/credit/v1/credit_lines"
    )
    SALAMPAY_REQUEST_TIMEOUT_SECONDS: float = 20.0

    # Click-Ad (توی‌چشم) advertising service. NOT wrapped by the Basalam SDK.
    # The click-ad settings / product-ad list / product-ad activation live on the
    # pelekan host; the ad-wallet "current user" credit endpoint lives on the
    # separate intheeye ads host. Called via the typed ClickAdSDK
    # (setup/sdks/clickad) with the forwarded user bearer token.
    CLICKAD_PELEKAN_BASE_URL: str = "https://api-pelekan.basalam.com"
    CLICKAD_INTHEEYE_BASE_URL: str = "https://api-intheeye.basalam.com"
    CLICKAD_REQUEST_TIMEOUT_SECONDS: float = 20.0

    BASALAM_CLIENT_ID: str = ""
    BASALAM_CLIENT_SECRET: str = ""
    BASALAM_SDK_TIMEOUT_SECONDS: float = 20.0

    BASALAM_SDK_RETRY_MAX_ATTEMPTS: int = 3
    BASALAM_SDK_RETRY_BACKOFF_SECONDS: float = 0.5
    BASALAM_SDK_RETRY_BACKOFF_CAP_SECONDS: float = 4.0

    # ----- product_comparison tool -----
    # Model used for same-product matching. Falls back to OPENROUTER_TOOL_MODEL.
    PRODUCT_COMPARISON_LLM_MODEL: str = ""
    PRODUCT_COMPARISON_REQUEST_TIMEOUT_SECONDS: float = 30.0
    # Max candidates returned per provider (Basalam / Torob / Digikala).
    PRODUCT_COMPARISON_MAX_PROVIDER_RESULTS: int = 24
    # Max candidates sent to the LLM in one call.
    PRODUCT_COMPARISON_MAX_LLM_CANDIDATES: int = 12
    # Below this confidence the LLM's "match" verdict is downgraded to uncertain.
    PRODUCT_COMPARISON_AUTO_MATCH_CONFIDENCE_MIN: float = 0.80
    # Parallelism for downloading selected candidate images for the LLM collage.
    PRODUCT_COMPARISON_IMAGE_DOWNLOAD_BATCH_SIZE: int = 12
    CACHE_PRODUCT_COMPARE_IMAGE_SEARCH_TTL_SECONDS: int = 15 * 86400
    CACHE_PRODUCT_COMPARE_DETAIL_TTL_SECONDS: int = 86400

    @field_validator("MAIN_POSTGRES_USER", "MAIN_POSTGRES_PASS")
    @classmethod
    def _require_postgres_credential(cls, value: str, info) -> str:
        # Fail loud if the credential is missing or still the sentinel.
        # Empty strings are also rejected — Postgres auth would fail anyway,
        # so surface the misconfiguration at startup.
        if value is None or value == "" or value == _REQUIRED_SENTINEL:
            raise ValueError(
                f"{info.field_name} must be set via env var; "
                "refusing to start with the placeholder default"
            )
        return value

    @property
    def project_root(self) -> Path:
        return Path(os.path.dirname(__file__)).parent.parent.absolute()

    @property
    def mcp_root_dir(self) -> Path:
        if self.MCP_ROOT_DIR:
            return Path(self.MCP_ROOT_DIR).expanduser().resolve()
        return (self.project_root / "src" / "mcps").resolve()

    @property
    def skills_root_dir(self) -> Path:
        if self.SKILLS_ROOT_DIR:
            return Path(self.SKILLS_ROOT_DIR).expanduser().resolve()
        return (self.project_root / "src" / "skills").resolve()

    @property
    def main_db_connection_string(self) -> str:
        from urllib.parse import quote_plus

        encoded_pass = quote_plus(self.MAIN_POSTGRES_PASS)
        return (
            "postgresql+asyncpg://"
            f"{self.MAIN_POSTGRES_USER}:{encoded_pass}"
            f"@{self.resolved_main_postgres_host}:{self.MAIN_POSTGRES_PORT}"
            f"/{self.MAIN_POSTGRES_DATABASE}"
        )

    @property
    def main_asyncpg_dsn(self) -> str:
        from urllib.parse import quote_plus

        encoded_pass = quote_plus(self.MAIN_POSTGRES_PASS)
        return (
            "postgresql://"
            f"{self.MAIN_POSTGRES_USER}:{encoded_pass}"
            f"@{self.resolved_main_postgres_host}:{self.MAIN_POSTGRES_PORT}"
            f"/{self.MAIN_POSTGRES_DATABASE}"
        )

    @property
    def agno_db_connection_string(self) -> str:
        return self.main_db_connection_string

    @property
    def resolved_main_postgres_host(self) -> str:
        host = str(self.MAIN_POSTGRES_HOST or "").strip() or "localhost"
        if self.APP_ENV != "local":
            return host

        normalized_host = host.lower()
        if normalized_host == "postgres" or normalized_host.endswith(".svc.cluster.local"):
            return str(self.LOCAL_MAIN_POSTGRES_HOST or "").strip() or "localhost"

        return host

    @property
    def admin_allowed_origins(self) -> list[str]:
        raw = self.ADMIN_ALLOWED_ORIGINS or ""
        # dict.fromkeys preserves order and dedupes the resulting origin list,
        # so callers can append production hostnames via env var without
        # worrying about overlaps with the in-source default.
        return list(dict.fromkeys(item.strip() for item in raw.split(",") if item.strip()))

    @property
    def product_auto_edit_fields(self) -> set[str]:
        return {item.strip().lower() for item in self.PRODUCT_AUTO_EDIT_FIELDS.split(",") if item.strip()}

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=Path(os.path.dirname(__file__)).parent.parent.absolute().__str__() + "/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config()


class _ConfigProxy:
    """Lazy module-level config proxy.

    Old call sites use ``from setup.config import config`` and reach for
    attributes (``config.DEBUG``). Resolving on every attribute access lets
    tests override env vars before the first read without changing import
    order across the whole project.
    """

    def __getattr__(self, name: str):
        return getattr(get_config(), name)

    def __setattr__(self, name: str, value) -> None:  # pragma: no cover - guard
        raise AttributeError("Config is immutable; set environment variables instead")


config = _ConfigProxy()
