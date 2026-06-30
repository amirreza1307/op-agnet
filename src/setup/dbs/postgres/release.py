import logging

from setup.dbs.postgres.main import main_release_postgres

logger = logging.getLogger(__name__)


async def release_all_postgres_connections() -> None:
    try:
        await main_release_postgres()
    except Exception:
        logger.exception("release_all_postgres_connections: failed")
