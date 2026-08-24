from httpx import AsyncClient

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
