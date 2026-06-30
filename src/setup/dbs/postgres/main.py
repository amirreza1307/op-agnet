import inspect
import logging
from typing import Any, Optional

from basalam.backbone_orm.postgres_manager import PostgresManager, ConnectionConfig, DriverEnum

from setup.config import config
from setup.request_context import RequestContext

logger = logging.getLogger(__name__)

resolved_main_postgres_host = config.resolved_main_postgres_host
if resolved_main_postgres_host != config.MAIN_POSTGRES_HOST:
    logger.warning(
        "Resolved main Postgres host '%s' to '%s' for local runtime",
        config.MAIN_POSTGRES_HOST,
        resolved_main_postgres_host,
    )

main_postgres_manager = PostgresManager(
    ConnectionConfig(
        pool_min_size=config.MAIN_POSTGRES_CONNECTION_POOL_MIN_SIZE,
        pool_max_size=config.MAIN_POSTGRES_CONNECTION_POOL_MAX_SIZE,
        pool_acquire_timeout=config.MAIN_POSTGRES_ACQUIRE_TIMEOUT_IN_SECONDS,
        user=config.MAIN_POSTGRES_USER,
        password=config.MAIN_POSTGRES_PASS,
        host=resolved_main_postgres_host,
        port=config.MAIN_POSTGRES_PORT,
        db=config.MAIN_POSTGRES_DATABASE,
        pool_max_inactive_connection_lifetime=config.MAIN_POSTGRES_POOL_MAX_INACTIVE_CONNECTION_LIFETIME,
        timeout=config.MAIN_POSTGRES_TIMEOUT,
    )
)


def driver():
    if config.APP_ENV == 'test':
        return DriverEnum.TEST
    elif RequestContext.get() is None:
        return DriverEnum.SINGLE
    else:
        return DriverEnum.POOL


def _pool_driver():
    return main_postgres_manager._PostgresManager__drivers[DriverEnum.POOL]


def _acquires_dict() -> dict:
    return _pool_driver()._PoolDriver__acquires


def _underlying_asyncpg(wrapper) -> Optional[Any]:
    return getattr(wrapper, "_PostgresConnection__connection", None)


def _is_broken(raw) -> bool:
    if raw is None:
        return True
    try:
        if raw.is_closed():
            return True
    except Exception:
        pass
    if getattr(raw, "_aborted", False):
        return True
    protocol = getattr(raw, "_protocol", None)
    if protocol is not None:
        is_cancelling = getattr(protocol, "_is_cancelling", None)
        try:
            if callable(is_cancelling) and is_cancelling():
                return True
        except Exception:
            pass
    return False


def _evict_sync(key: Any):
    if key is None:
        return None
    try:
        acquires = _acquires_dict()
    except Exception:
        logger.exception("evict_sync: cannot access PoolDriver internals")
        return None
    try:
        entry = acquires.pop(key, None)
    except Exception:
        logger.exception("evict_sync: pop from acquires map failed")
        return None
    if entry is None:
        return None
    try:
        if not isinstance(entry, tuple) or len(entry) < 2:
            return entry
        wrapper, raw_or_ctx = entry[0], entry[1]
    except Exception:
        logger.exception("evict_sync: unexpected acquires entry shape: %r", entry)
        return entry
    raw = None
    try:
        raw = _underlying_asyncpg(wrapper) if wrapper is not None else None
    except Exception:
        logger.debug("evict_sync: failed to extract raw asyncpg connection", exc_info=True)
    for candidate in (raw, raw_or_ctx):
        if candidate is None:
            continue
        try:
            terminate = getattr(candidate, "terminate", None)
        except Exception:
            terminate = None
        if not callable(terminate):
            continue
        try:
            terminate()
            return entry
        except Exception:
            logger.debug("evict_sync: terminate raised", exc_info=True)
    return entry


async def main_postgres():
    key = RequestContext.get()
    drv = driver()
    if drv is DriverEnum.POOL and key is not None:
        try:
            cached = _acquires_dict().get(key)
        except Exception:
            cached = None
        if cached is not None:
            raw = _underlying_asyncpg(cached[0])
            if _is_broken(raw):
                logger.warning(
                    "main_postgres: evicting broken cached connection before reuse"
                )
                _evict_sync(key)
    return await main_postgres_manager.acquire(drv, key)


async def _close_single_driver(target: Any) -> None:
    field_name = "_SingleDriver__connection"
    if not hasattr(target, field_name):
        return
    entry = getattr(target, field_name, None)
    if entry is None:
        return
    try:
        setattr(target, field_name, None)
    except Exception:
        pass
    raw_conn = entry[1] if isinstance(entry, tuple) and len(entry) > 1 else None
    if raw_conn is None:
        return
    try:
        close = getattr(raw_conn, "close", None)
        if close is None:
            return
        result = close()
        if inspect.isawaitable(result):
            await result
    except Exception:
        logger.exception("single driver close failed; terminating")
        terminate = getattr(raw_conn, "terminate", None)
        if callable(terminate):
            try:
                terminate()
            except Exception:
                logger.debug("terminate raised", exc_info=True)


async def _release_via_driver(drv: DriverEnum, key: Any) -> None:
    drivers = main_postgres_manager._PostgresManager__drivers
    target = drivers[drv]
    if drv is DriverEnum.SINGLE:
        await _close_single_driver(target)
        return
    try:
        result = target.release(key)
    except TypeError:
        result = target.release()
    if inspect.isawaitable(result):
        await result


def _safe_evict(key: Any) -> None:
    try:
        _evict_sync(key)
    except Exception:
        logger.exception("main_release_postgres: eviction itself raised")


async def main_release_postgres():
    key = RequestContext.get()
    drv = driver()
    if drv is not DriverEnum.POOL:
        try:
            await _release_via_driver(drv, key)
        except Exception:
            logger.exception("main_release_postgres: %s release failed", drv.value)
        return
    try:
        return await main_postgres_manager.release(drv, key)
    except BaseException as exc:
        if isinstance(exc, Exception):
            logger.warning(
                "main_release_postgres: pool release raised %s; force-evicting entry",
                type(exc).__name__,
            )
        else:
            logger.warning(
                "main_release_postgres: pool release interrupted by %s; force-evicting entry",
                type(exc).__name__,
            )
        _safe_evict(key)
        if isinstance(exc, Exception):
            return
        raise
