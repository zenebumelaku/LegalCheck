from typing import Generator

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base


@pytest.fixture(autouse=True)
def use_test_rate_limiter(monkeypatch):
    from app.core.rate_limit import get_rate_limiter
    from app.main import app

    class NoopRateLimiter:
        def check(self, request, bucket: str, limit: int) -> None:
            return None

    app.dependency_overrides[get_rate_limiter] = lambda: NoopRateLimiter()
    yield
    app.dependency_overrides.pop(get_rate_limiter, None)


@pytest.fixture
def db_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, connection_record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        connection_record.info["foreign_keys_enabled"] = True
        cursor.close()

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    session_factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    with session_factory() as session:
        yield session
