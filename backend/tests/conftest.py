from typing import Generator

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base


@pytest.fixture
def db_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
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
