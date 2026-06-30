import asyncio
import logging

logger = logging.getLogger(__name__)

_previous_asyncio_exception_handler = None


def _is_benign_windows_connection_reset(context: dict) -> bool:
    exception = context.get("exception")
    if not isinstance(exception, ConnectionResetError):
        return False

    if getattr(exception, "winerror", None) != 10054:
        return False

    handle = context.get("handle")
    callback_repr = repr(handle) if handle is not None else ""
    message = str(context.get("message") or "")
    return "_call_connection_lost" in callback_repr or "_call_connection_lost" in message


def _is_asyncpg_orphaned_release(context: dict) -> bool:
    exception = context.get("exception")
    if exception is None:
        return False
    exc_module = getattr(type(exception), "__module__", "") or ""
    exc_name = type(exception).__name__
    if not (exc_module.startswith("asyncpg") and exc_name == "ConnectionDoesNotExistError"):
        return False
    message = str(context.get("message") or "")
    if "Task exception was never retrieved" not in message:
        return False
    future = context.get("future")
    future_repr = repr(future) if future is not None else ""
    return "PoolConnectionHolder.release" in future_repr or "pool.py" in future_repr


def install_asyncio_exception_filter() -> None:
    global _previous_asyncio_exception_handler

    loop = asyncio.get_running_loop()
    _previous_asyncio_exception_handler = loop.get_exception_handler()

    def _handler(loop: asyncio.AbstractEventLoop, context: dict) -> None:
        if _is_benign_windows_connection_reset(context):
            logger.debug("Ignoring benign Windows connection reset from closed MCP client connection")
            return

        if _is_asyncpg_orphaned_release(context):
            logger.debug(
                "Ignoring orphaned asyncpg pool.release task (client disconnected mid-stream)"
            )
            return

        if _previous_asyncio_exception_handler is not None:
            _previous_asyncio_exception_handler(loop, context)
        else:
            loop.default_exception_handler(context)

    loop.set_exception_handler(_handler)


def restore_asyncio_exception_filter() -> None:
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(_previous_asyncio_exception_handler)
