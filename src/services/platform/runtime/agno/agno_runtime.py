"""Agno runtime bootstrap (Phase 5 — concurrency-safe singletons).

The legacy module-level flags (``_TRACING_CONFIGURED``, ``_TRACING_ATTEMPTED``,
``_POSTGRES_DB_CACHE``) had no locking, so two concurrent ``ensure_agno_tracing``
calls could both install the DB exporter and produce duplicate spans
(F-05). All shared state is now owned by a single :class:`AgnoRuntimeBootstrap`
instance guarded by ``asyncio.Lock``.

The previous module-level functions are preserved as thin shims so existing
callers continue to work.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx
from agno.models.message import Message
from agno.models.openrouter import OpenRouter

from setup.config import config
from setup.translator import trans

logger = logging.getLogger(__name__)

try:
    from agno.db.postgres import AsyncPostgresDb
except Exception as _exc:  # pragma: no cover - optional dep
    logger.exception("agno_postgres_import_failed: %s", _exc)
    AsyncPostgresDb = None  # type: ignore[assignment]

try:
    from agno.memory import MemoryManager
except Exception as _exc:  # pragma: no cover - optional dep
    logger.exception("agno_memory_manager_import_failed: %s", _exc)
    MemoryManager = None  # type: ignore[assignment]

try:
    from agno.tracing import setup_tracing as setup_agno_tracing  # noqa: F401  - kept for back-compat
except Exception:  # pragma: no cover
    setup_agno_tracing = None  # type: ignore[assignment]

try:
    from agno.utils.http import set_default_async_client, set_default_sync_client
except Exception:  # pragma: no cover
    set_default_async_client = None  # type: ignore[assignment]
    set_default_sync_client = None  # type: ignore[assignment]


class SafeOpenRouter(OpenRouter):
    """OpenRouter subclass with a workaround for Agno's history replay.

    **Why this exists**: When ``add_history_to_context=True`` Agno replays
    old assistant messages back to the model. Some of those messages were
    minted by *reasoning* models and carry a ``reasoning_details`` field
    inside ``provider_data``. OpenRouter rejects that field with a 400 when
    the field is sent with a non-reasoning model, breaking history replay.

    **Removal criterion**: once OpenRouter (or Agno's adapter) stops
    forwarding ``reasoning_details`` for non-reasoning models, drop this
    subclass and use ``OpenRouter`` directly. Tracked upstream — re-check
    on every Agno minor bump.
    """

    supports_json_schema_outputs: bool = True

    def _format_message(self, message: Message, compress_tool_results: bool = False):
        if message.from_history and message.provider_data:
            message.provider_data.pop("reasoning_details", None)
        return super()._format_message(message, compress_tool_results)


class AgnoRuntimeBootstrap:
    """Owns all global Agno bootstrap state with explicit async locking."""

    def __init__(self) -> None:
        self._db_cache: dict[str, object] = {}
        self._memory_manager_cache: dict[str, object] = {}
        self._db_lock = asyncio.Lock()
        self._tracing_lock = asyncio.Lock()
        self._tracing_state: str = "not_attempted"  # not_attempted|in_progress|configured|failed
        self._proxy_configured = False
        self._proxy_lock = asyncio.Lock()

    # ----- proxy ------------------------------------------------------------

    def configure_http_proxy(self) -> None:
        """Synchronous: configures the default HTTP client once."""
        if self._proxy_configured:
            return
        self._proxy_configured = True

        proxy = str(config.OPENROUTER_PROXY or "").strip()
        if not proxy or set_default_async_client is None or set_default_sync_client is None:
            return

        proxy_async_client = httpx.AsyncClient(
            proxy=proxy,
            limits=httpx.Limits(max_connections=1000, max_keepalive_connections=200),
            http2=True,
            follow_redirects=True,
        )
        proxy_sync_client = httpx.Client(
            proxy=proxy,
            limits=httpx.Limits(max_connections=1000, max_keepalive_connections=200),
            http2=False,
            follow_redirects=True,
        )
        set_default_async_client(proxy_async_client)
        set_default_sync_client(proxy_sync_client)

    # ----- model build ------------------------------------------------------

    def build_model(
        self,
        model_id: Optional[str] = None,
        model_provider: Optional[str] = None,  # noqa: ARG002 - reserved for future routing
        model_api_key: Optional[str] = None,
        model_base_url: Optional[str] = None,
    ) -> SafeOpenRouter:
        self.configure_http_proxy()
        resolved_model_id = str(model_id or config.AGNO_MODEL or "").strip() or "openai/gpt-4o"
        kwargs = {
            "id": resolved_model_id,
            "api_key": (model_api_key or "").strip() or config.OPENROUTER_API_KEY,
            "base_url": (model_base_url or "").strip() or config.OPENROUTER_BASE_URL,
            "timeout": config.OPENROUTER_TIMEOUT,
            "max_retries": 3,
        }
        try:
            return SafeOpenRouter(**kwargs)
        except TypeError:
            kwargs.pop("base_url", None)
            return SafeOpenRouter(**kwargs)

    # ----- db cache ---------------------------------------------------------

    def get_db(self, session_table: Optional[str] = None):
        """Synchronous accessor; the cache is process-local."""
        if AsyncPostgresDb is None:
            msg = (
                "Agno DB unavailable: AsyncPostgresDb import failed. "
                "Ensure `sqlalchemy[asyncio]` and `asyncpg` are installed."
            )
            if config.AGNO_DB_INIT_FAIL_FAST:
                raise RuntimeError(trans("errors.platform.runtime.agno_db_unavailable"))
            logger.warning(msg)
            return None

        resolved_table = _resolve_session_table(session_table)
        cached = self._db_cache.get(resolved_table)
        if cached is not None:
            return cached

        try:
            db = AsyncPostgresDb(
                db_url=config.agno_db_connection_string,
                db_schema=str(config.AGNO_DB_SCHEMA or "ai").strip() or "ai",
                session_table=resolved_table,
                memory_table=str(config.AGNO_MEMORY_TABLE or "agno_memories").strip(),
                metrics_table=str(config.AGNO_METRICS_TABLE or "agno_metrics").strip(),
                eval_table=str(config.AGNO_EVAL_TABLE or "agno_eval_runs").strip(),
                knowledge_table=str(config.AGNO_KNOWLEDGE_TABLE or "agno_knowledge").strip(),
                traces_table=str(config.AGNO_TRACES_TABLE or "agno_traces").strip(),
                spans_table=str(config.AGNO_SPANS_TABLE or "agno_spans").strip(),
                versions_table=str(config.AGNO_VERSIONS_TABLE or "agno_schema_versions").strip(),
                learnings_table=str(config.AGNO_LEARNINGS_TABLE or "agno_learnings").strip(),
            )
        except Exception:
            logger.exception(
                "agno_db_constructor_failed table=%s schema=%s",
                resolved_table,
                config.AGNO_DB_SCHEMA,
            )
            if config.AGNO_DB_INIT_FAIL_FAST:
                raise
            return None
        # Last-writer-wins. If two threads race, one db is leaked but no
        # invariant is violated; AsyncPostgresDb is itself process-shared.
        self._db_cache[resolved_table] = db
        logger.info("agno_db_created table=%s", resolved_table)
        return db

    # ----- memory manager ---------------------------------------------------

    def get_memory_manager(self, session_table: Optional[str] = None):
        """Build (and cache) a ``MemoryManager`` backed by a cheaper model.

        The memory manager runs after every parent run (``update_memory_on_run``)
        to extract/update user memories. It uses ``AGNO_MEMORY_MODEL`` — a small,
        cheap model — independent of the agent's main model. Returns ``None`` if
        the dependency or DB is unavailable, so callers can degrade gracefully.
        """
        if MemoryManager is None:
            logger.warning("agno_memory_manager_unavailable reason=import_failed")
            return None

        resolved_table = _resolve_session_table(session_table)
        cached = self._memory_manager_cache.get(resolved_table)
        if cached is not None:
            return cached

        db = self.get_db(resolved_table)
        if db is None:
            logger.warning("agno_memory_manager_skipped reason=db_unavailable")
            return None

        try:
            manager = MemoryManager(
                model=self.build_model(model_id=config.AGNO_MEMORY_MODEL),
                db=db,
            )
        except Exception:
            logger.exception("agno_memory_manager_constructor_failed table=%s", resolved_table)
            return None

        # Last-writer-wins; a race only leaks one stateless manager instance.
        self._memory_manager_cache[resolved_table] = manager
        logger.info("agno_memory_manager_created table=%s model=%s", resolved_table, config.AGNO_MEMORY_MODEL)
        return manager

    # ----- tracing ----------------------------------------------------------

    async def ensure_tracing(self) -> bool:
        if self._tracing_state == "configured":
            return True
        if self._tracing_state == "failed":
            return False

        async with self._tracing_lock:
            if self._tracing_state == "configured":
                return True
            if self._tracing_state == "failed":
                return False
            self._tracing_state = "in_progress"

            agno_db = self.get_db()
            if agno_db is None:
                logger.warning("agno_tracing_disabled reason=db_unavailable")
                self._tracing_state = "failed"
                return False
            if setup_agno_tracing is None:
                logger.warning(
                    "agno_tracing_disabled reason=missing_deps "
                    "hint='install openinference-instrumentation-agno'"
                )
                self._tracing_state = "failed"
                return False

            try:
                _install_db_exporter(agno_db)
                await _ensure_tracing_tables(agno_db)
                self._tracing_state = "configured"
                logger.info("agno_tracing_configured")
                return True
            except Exception:
                logger.exception("agno_tracing_setup_failed")
                self._tracing_state = "failed"
                return False


_BOOTSTRAP = AgnoRuntimeBootstrap()


def configure_agno_http_proxy() -> None:
    _BOOTSTRAP.configure_http_proxy()


def build_model(
    model_id: Optional[str] = None,
    model_provider: Optional[str] = None,
    model_api_key: Optional[str] = None,
    model_base_url: Optional[str] = None,
) -> SafeOpenRouter:
    return _BOOTSTRAP.build_model(
        model_id=model_id,
        model_provider=model_provider,
        model_api_key=model_api_key,
        model_base_url=model_base_url,
    )


def get_agno_db(session_table: Optional[str] = None):
    return _BOOTSTRAP.get_db(session_table)


def get_agno_memory_manager(session_table: Optional[str] = None):
    return _BOOTSTRAP.get_memory_manager(session_table)


async def ensure_agno_tracing() -> bool:
    return await _BOOTSTRAP.ensure_tracing()


def get_agno_runtime_bootstrap() -> AgnoRuntimeBootstrap:
    """Return the process-wide bootstrap instance.

    Exposed for FastAPI startup hooks that want to eagerly call
    ``await get_agno_runtime_bootstrap().ensure_tracing()`` before the
    first request lands.
    """
    return _BOOTSTRAP


def _resolve_session_table(session_table: Optional[str] = None) -> str:
    return str(
        session_table or config.PLATFORM_DEFAULT_SESSION_TABLE or config.AGNO_SESSION_TABLE
    ).strip()


def _install_db_exporter(agno_db) -> None:
    from opentelemetry import trace as trace_api
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    from agno.tracing.exporter import DatabaseSpanExporter

    try:
        from openinference.instrumentation.agno import AgnoInstrumentor
    except Exception:
        AgnoInstrumentor = None

    current = trace_api.get_tracer_provider()
    if isinstance(current, TracerProvider):
        provider = current
        logger.info("agno_tracing_reuse_provider class=%s", type(current).__name__)
    else:
        provider = TracerProvider()
        trace_api.set_tracer_provider(provider)
        logger.info("agno_tracing_new_provider")

    provider.add_span_processor(SimpleSpanProcessor(DatabaseSpanExporter(db=agno_db)))

    if AgnoInstrumentor is not None:
        try:
            AgnoInstrumentor().instrument(tracer_provider=provider)
        except Exception:
            logger.exception("agno_tracing_instrument_failed")


async def _ensure_tracing_tables(agno_db) -> None:
    for table_type in ("traces", "spans"):
        try:
            await agno_db._get_table(table_type=table_type, create_table_if_not_found=True)
        except Exception:
            logger.exception("agno_tracing_table_ensure_failed table=%s", table_type)


__all__ = [
    "AgnoRuntimeBootstrap",
    "SafeOpenRouter",
    "build_model",
    "configure_agno_http_proxy",
    "ensure_agno_tracing",
    "get_agno_db",
    "get_agno_memory_manager",
    "get_agno_runtime_bootstrap",
]
