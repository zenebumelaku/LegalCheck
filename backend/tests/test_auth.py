from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_organization_membership, require_roles
from app.core.security import hash_access_token
from app.db.models import AuthSession, Organization, OrganizationMembership, User
from app.db.session import get_db
from app.main import app
from app.schemas.auth import RegisterRequest


@pytest.fixture
def auth_client(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


def register(client: TestClient, email: str = "user@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "  Example User  ",
            "email": email,
            "password": "a-long-test-password",
        },
    )
    assert response.status_code == 201
    return response.json()


def login(client: TestClient, email: str = "user@example.com"):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "a-long-test-password"},
    )


def test_registration_normalizes_email_hashes_password_and_hides_hash(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    response_data = register(auth_client, "  USER@Example.com  ")

    user = db_session.scalar(select(User).where(User.email == "user@example.com"))
    assert user is not None
    assert user.password_hash.startswith("$argon2id$")
    assert user.password_hash != "a-long-test-password"
    assert response_data["email"] == "user@example.com"
    assert response_data["name"] == "Example User"
    assert response_data["role"] == "user"
    assert "password" not in response_data
    assert "password_hash" not in response_data


def test_registration_rejects_duplicate_normalized_email(
    auth_client: TestClient,
) -> None:
    register(auth_client)

    duplicate = auth_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Duplicate",
            "email": "USER@EXAMPLE.COM",
            "password": "another-long-test-password",
        },
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["message"] == (
        "An account with that email already exists."
    )


def test_registration_rejects_weak_password() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Example",
            email="valid@example.com",
            password="short",
        )


def test_registration_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Example",
            email="not-an-email",
            password="a-long-test-password",
        )


def test_registration_rejects_client_supplied_authorization_fields(
    auth_client: TestClient,
) -> None:
    response = auth_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Example User",
            "email": "user@example.com",
            "password": "a-long-test-password",
            "role": "admin",
            "user_id": "00000000-0000-0000-0000-000000000001",
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "email,password",
    [
        ("user@example.com", "incorrect-password"),
        ("missing@example.com", "incorrect-password"),
    ],
)
def test_login_failure_uses_generic_error(
    auth_client: TestClient,
    email: str,
    password: str,
) -> None:
    register(auth_client)
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Email or password is incorrect."
    assert "access_token" not in response.json()


def test_login_authenticates_me_and_stores_only_a_token_hash(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    user = register(auth_client)
    response = login(auth_client, "USER@example.com")

    assert response.status_code == 200
    token = response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user"]["id"] == user["id"]
    assert "password_hash" not in response.json()["user"]

    stored_session = db_session.scalar(
        select(AuthSession).where(AuthSession.user_id == UUID(user["id"]))
    )
    assert stored_session is not None
    assert stored_session.token_hash == hash_access_token(token)
    assert stored_session.token_hash != token

    me = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"
    assert "password_hash" not in me.json()


def test_protected_me_requires_a_valid_bearer_token(auth_client: TestClient) -> None:
    missing = auth_client.get("/api/v1/auth/me")
    invalid = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"


def test_logout_revokes_the_current_session(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    register(auth_client)
    token = login(auth_client).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    logout_response = auth_client.post("/api/v1/auth/logout", headers=headers)
    me_after_logout = auth_client.get("/api/v1/auth/me", headers=headers)

    assert logout_response.status_code == 204
    assert me_after_logout.status_code == 401
    auth_session = db_session.scalar(
        select(AuthSession).where(AuthSession.token_hash == hash_access_token(token))
    )
    assert auth_session is not None
    assert auth_session.revoked_at is not None


def test_password_reset_request_does_not_claim_email_delivery(
    auth_client: TestClient,
) -> None:
    known = auth_client.post(
        "/api/v1/auth/password-reset-request",
        json={"email": "user@example.com"},
    )
    unknown = auth_client.post(
        "/api/v1/auth/password-reset-request",
        json={"email": "missing@example.com"},
    )

    assert known.status_code == 202
    assert known.json() == unknown.json()
    assert "after email delivery is configured" in known.json()["message"]


def test_organization_membership_helper_uses_authenticated_user(
    db_session: Session,
) -> None:
    user = User(
        name="Member",
        email="member@example.com",
        password_hash="test-hash",
    )
    organization = Organization(name="Example Org", organization_type="employer")
    membership = OrganizationMembership(
        user=user,
        organization=organization,
        membership_role="member",
    )
    db_session.add(membership)
    db_session.commit()

    assert (
        get_organization_membership(
            db_session,
            user,
            organization.id,
            allowed_roles={"member", "admin"},
        )
        is membership
    )

    with pytest.raises(HTTPException) as error:
        get_organization_membership(
            db_session,
            user,
            organization.id,
            allowed_roles={"admin"},
        )
    assert error.value.status_code == 403


def test_role_dependency_rejects_unlisted_roles(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    register(auth_client)
    user = db_session.scalar(select(User).where(User.email == "user@example.com"))
    assert user is not None
    role_dependency = require_roles("admin")

    with pytest.raises(HTTPException) as error:
        role_dependency(user)
    assert error.value.status_code == 403
