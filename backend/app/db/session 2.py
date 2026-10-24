from functools import lru_cache

from sqlalchemy import Engine, create_engine, text

from app.core.config import settings


class DatabaseConfigurationError(RuntimeError):
    pass


@lru_cache
def get_engine() -> Engine:
    if not settings.database_url:
        raise DatabaseConfigurationError("DATABASE_URL is not configured.")
    return create_engine(settings.database_url, pool_pre_ping=True)


def check_database_connection() -> None:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
