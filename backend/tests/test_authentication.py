from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import AppleIdentity, User
from app.services.email_verification import hash_code, validate_harvard_email


def test_harvard_domain_validation_is_exact() -> None:
    allowed = ["harvard.edu"]
    assert validate_harvard_email(" Student@HARVARD.EDU ", allowed) == "student@harvard.edu"


def test_verification_hash_is_peppered() -> None:
    assert hash_code("123456", "first") != hash_code("123456", "second")
    assert "123456" not in hash_code("123456", "first")


async def test_development_sign_in_and_email_verification(client: AsyncClient) -> None:
    sign_in = await client.post(
        "/api/v1/auth/development", json={"display_name": "Development Member"}
    )
    assert sign_in.status_code == 200
    token = sign_in.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    requested = await client.post(
        "/api/v1/auth/verification/request",
        json={"email": "dev@harvard.edu"},
        headers=headers,
    )
    assert requested.status_code == 200
    code = requested.json()["development_code"]
    assert len(code) == 6

    verified = await client.post(
        "/api/v1/auth/verification/confirm",
        json={"email": "dev@harvard.edu", "code": code},
        headers=headers,
    )
    assert verified.status_code == 200
    assert verified.json()["harvard_email_verified"] is True

    reused = await client.post(
        "/api/v1/auth/verification/confirm",
        json={"email": "dev@harvard.edu", "code": code},
        headers=headers,
    )
    assert reused.status_code == 400
    assert reused.json()["error"]["code"] == "code_expired"


async def test_development_fixture_ids_create_distinct_local_users(client: AsyncClient) -> None:
    first = await client.post(
        "/api/v1/auth/development",
        json={"display_name": "Load Buyer One", "fixture_id": "load-buyer-1"},
    )
    second = await client.post(
        "/api/v1/auth/development",
        json={"display_name": "Load Buyer Two", "fixture_id": "load-buyer-2"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["user"]["id"] != second.json()["user"]["id"]


async def test_rejects_non_harvard_domain(client: AsyncClient) -> None:
    sign_in = await client.post("/api/v1/auth/development", json={})
    token = sign_in.json()["access_token"]
    response = await client.post(
        "/api/v1/auth/verification/request",
        json={"email": "person@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "email_domain_not_allowed"


async def test_profile_update_and_account_deletion_revoke_identity(
    client: AsyncClient, session: AsyncSession
) -> None:
    sign_in = await client.post("/api/v1/auth/development", json={"display_name": "Original Name"})
    token = sign_in.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    updated = await client.patch(
        "/api/v1/auth/profile", json={"display_name": "Updated Name"}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Updated Name"

    deleted = await client.delete("/api/v1/auth/account", headers=headers)
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 401

    user = await session.scalar(select(User).where(User.display_name == "Deleted Yard member"))
    assert user is not None
    assert user.deleted_at is not None
    identity = await session.scalar(select(AppleIdentity).where(AppleIdentity.user_id == user.id))
    assert identity is None
