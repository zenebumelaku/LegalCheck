from functools import lru_cache
from typing import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


class DatabaseConfigurationError(RuntimeError):
    pass


@lru_cache
def get_engine() -> Engine:
    if not settings.database_url:
        raise DatabaseConfigurationError("DATABASE_URL is not configured.")
    return create_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), class_=Session, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_connection() -> None:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
