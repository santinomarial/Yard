import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationStatus
from app.services.notifications import deliver_pending_notifications, enqueue_notification


class RecordingProvider:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.delivered: list[str] = []

    async def send(self, token: str, notification) -> None:  # type: ignore[no-untyped-def]
        if self.fail:
            raise RuntimeError("temporary APNs failure")
        self.delivered.append(token)


async def test_device_registration_is_idempotent_and_revocable(client: AsyncClient) -> None:
    sign_in = await client.post("/api/v1/auth/development", json={})
    headers = {"Authorization": f"Bearer {sign_in.json()['access_token']}"}
    payload = {"token": "ab" * 32, "environment": "sandbox"}

    first = await client.post("/api/v1/notifications/devices", json=payload, headers=headers)
    second = await client.post("/api/v1/notifications/devices", json=payload, headers=headers)
    revoked = await client.delete(
        f"/api/v1/notifications/devices/{first.json()['id']}", headers=headers
    )

    assert first.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert revoked.status_code == 204


async def test_notification_outbox_is_idempotent_and_retries_failures(
    client: AsyncClient, session: AsyncSession
) -> None:
    sign_in = await client.post("/api/v1/auth/development", json={})
    user_id = uuid.UUID(sign_in.json()["user"]["id"])
    headers = {"Authorization": f"Bearer {sign_in.json()['access_token']}"}
    await client.post(
        "/api/v1/notifications/devices",
        json={"token": "cd" * 32, "environment": "sandbox"},
        headers=headers,
    )
    first = await enqueue_notification(
        session,
        user_id=user_id,
        notification_type="new_message",
        title="New message",
        body="Hello",
        idempotency_key="test-notification-once",
    )
    duplicate = await enqueue_notification(
        session,
        user_id=user_id,
        notification_type="new_message",
        title="New message",
        body="Hello",
        idempotency_key="test-notification-once",
    )
    await session.commit()

    failing = RecordingProvider(fail=True)
    sent, failed = await deliver_pending_notifications(session, failing)

    assert first.id == duplicate.id
    assert (sent, failed) == (0, 1)
    assert first.status == NotificationStatus.PENDING
    assert first.attempts == 1
