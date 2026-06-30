import inspect
import logging

from setup.config import config
from services.platform.graph.platform_cache_manager import PlatformCacheManager
from services.platform.runtime.agno.agno_runtime import ensure_agno_tracing
from tools.registry import load_registry

logger = logging.getLogger(__name__)


async def bootstrap_application_state() -> None:
    """Bring up runtime resources at app start.

    Schema management is **not** done here. Database tables are owned by
    the standalone scripts under ``scripts/schema/`` and must be applied
    out-of-band before the app starts. Running schema mutations from
    every worker on every boot races at scale and is not what we want.
    """
    logger.info("Bootstrapping managed resources and caches")
    steps = [
        ("load_tool_registry", load_registry),
        ("ensure_agno_tracing", ensure_agno_tracing),
    ]
    if config.PLATFORM_CACHE_EAGER_LOAD:
        steps.append(("load_platform_cache", PlatformCacheManager.load))

    for step_name, step_callable in steps:
        try:
            result = step_callable()
            if inspect.isawaitable(result):
                await result
            logger.info("Bootstrap step completed: %s", step_name)
        except Exception:
            logger.exception("Bootstrap step failed: %s", step_name)
            if config.BOOTSTRAP_FAIL_FAST:
                raise

    logger.info("Platform bootstrap completed")
