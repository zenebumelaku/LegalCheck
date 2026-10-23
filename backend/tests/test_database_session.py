from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from app.db import session as database_session


def test_request_database_dependency_closes_session(monkeypatch) -> None:
    request_session = Mock(spec=Session)
    monkeypatch.setattr(
        database_session,
        "get_session_factory",
        lambda: lambda: request_session,
    )
    dependency = database_session.get_db()

    assert next(dependency) is request_session
    with pytest.raises(StopIteration):
        next(dependency)

    request_session.close.assert_called_once_with()
    request_session.rollback.assert_not_called()


def test_request_database_dependency_rolls_back_errors(monkeypatch) -> None:
    request_session = Mock(spec=Session)
    monkeypatch.setattr(
        database_session,
        "get_session_factory",
        lambda: lambda: request_session,
    )
    dependency = database_session.get_db()
    next(dependency)

    with pytest.raises(RuntimeError, match="request failed"):
        dependency.throw(RuntimeError("request failed"))

    request_session.rollback.assert_called_once_with()
    request_session.close.assert_called_once_with()
