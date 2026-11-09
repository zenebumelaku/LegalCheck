from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes import health as health_routes
from app.db.models import User
from app.db.session import DatabaseConfigurationError, get_db
from app.main import app

pytestmark = pytest.mark.unit

client = TestClient(app)


@pytest.fixture
def health_client(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


def _login_with_role(
    test_client: TestClient,
    db_session: Session,
    role: str,
) -> str:
    email = f"{uuid4()}@example.com"
    password = "a-long-cache-health-test-password"
    registered = test_client.post(
        "/api/v1/auth/register",
        json={"name": "Cache Metrics Test", "email": email, "password": password},
    )
    assert registered.status_code == 201
    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.role = role
    db_session.commit()

    logged_in = test_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert logged_in.status_code == 200
    return logged_in.json()["access_token"]


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_returns_ready_when_database_is_available(
    monkeypatch,
) -> None:
    monkeypatch.setattr(health_routes, "check_database_connection", lambda: None)

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_endpoint_returns_unavailable_when_database_is_not_configured(
    monkeypatch,
) -> None:
    def raise_not_configured() -> None:
        raise DatabaseConfigurationError("DATABASE_URL is not configured.")

    monkeypatch.setattr(
        health_routes,
        "check_database_connection",
        raise_not_configured,
    )

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "http_error",
            "message": "The service is not ready.",
        }
    }


def test_cache_metrics_require_admin_role_and_report_process_scope(
    health_client: TestClient,
    db_session: Session,
) -> None:
    endpoint = "/api/v1/admin/legal-question-cache/metrics"
    assert health_client.get(endpoint).status_code == 401

    user_token = _login_with_role(health_client, db_session, "user")
    forbidden = health_client.get(
        endpoint,
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert forbidden.status_code == 403

    admin_token = _login_with_role(health_client, db_session, "admin")
    response = health_client.get(
        endpoint,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    metrics = response.json()
    assert metrics["scope"] == "process_local"
    assert "restart" in metrics["reset_behavior"]
    assert "not physically deleted" in metrics["logical_invalidations_meaning"]
    for metric in (
        "hits",
        "misses",
        "errors",
        "logical_invalidations",
        "provider_calls",
        "provider_calls_avoided",
    ):
        assert isinstance(metrics[metric], int)


def test_cache_health_reports_redis_unavailable_without_claiming_ai_health(
    health_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnavailableCache:
        def ping(self) -> bool:
            raise RedisConnectionError("synthetic connection failure")

    token = _login_with_role(health_client, db_session, "admin")
    endpoint = "/api/v1/health/answer-cache"
    assert health_client.get(endpoint).status_code == 401
    monkeypatch.setattr(
        health_routes,
        "get_legal_question_cache",
        lambda: UnavailableCache(),
    )

    response = health_client.get(
        endpoint,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "component": "redis_answer_cache",
        "redis_status": "unavailable",
        "ai_system_status": "not_assessed",
    }


def test_cache_health_reports_only_redis_reachability(
    health_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ReachableCache:
        def ping(self) -> bool:
            return True

    token = _login_with_role(health_client, db_session, "admin")
    monkeypatch.setattr(
        health_routes,
        "get_legal_question_cache",
        lambda: ReachableCache(),
    )

    response = health_client.get(
        "/api/v1/health/answer-cache",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "component": "redis_answer_cache",
        "redis_status": "reachable",
        "ai_system_status": "not_assessed",
    }
