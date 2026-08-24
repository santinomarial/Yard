import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Protocol

import httpx
import jwt
import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.notification import DeviceToken, NotificationOutbox, NotificationStatus
from app.models.pickup import PickupSession, PickupStatus
from app.models.reservation import Reservation, ReservationStatus, WaitlistEntry, WaitlistStatus

logger = structlog.get_logger()


class NotificationProvider(Protocol):
    async def send(self, token: str, notification: NotificationOutbox) -> None: ...


class DevelopmentNotificationProvider:
    async def send(self, token: str, notification: NotificationOutbox) -> None:
        logger.info(
            "development_push",
            token_suffix=token[-8:],
            notification_id=str(notification.id),
            notification_type=notification.notification_type,
        )


class APNSNotificationProvider:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        team_id = settings.apns_team_id
        key_id = settings.apns_key_id
        private_key = settings.apns_private_key
        if not team_id or not key_id or not private_key:
            raise RuntimeError("APNs credentials are not configured")
        self.settings = settings
        self.team_id = team_id
        self.key_id = key_id
        self.private_key = private_key
        self.client = client or httpx.AsyncClient(http2=True, timeout=10)

    async def send(self, token: str, notification: NotificationOutbox) -> None:
        authorization = jwt.encode(
            {"iss": self.team_id, "iat": int(time.time())},
            self.private_key.replace("\\n", "\n"),
            algorithm="ES256",
            headers={"kid": self.key_id},
        )
        host = "api.sandbox.push.apple.com" if self.settings.apns_sandbox else "api.push.apple.com"
        response = await self.client.post(
            f"https://{host}/3/device/{token}",
            headers={
                "authorization": f"bearer {authorization}",
                "apns-topic": self.settings.apns_bundle_id,
                "apns-push-type": "alert",
                "apns-priority": "10",
            },
            json={
                "aps": {
                    "alert": {"title": notification.title, "body": notification.body},
                    "sound": "default",
                },
                "deep_link": notification.deep_link,
                **notification.data,
            },
        )
        if response.status_code != 200:
            raise RuntimeError(f"APNs rejected notification with {response.status_code}")


def notification_provider(settings: Settings | None = None) -> NotificationProvider:
    configured = settings or get_settings()
    if configured.environment == "production":
        return APNSNotificationProvider(configured)
    return DevelopmentNotificationProvider()


async def enqueue_notification(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    notification_type: str,
    title: str,
    body: str,
    idempotency_key: str,
    deep_link: str | None = None,
    data: dict[str, str | int | float | bool | None] | None = None,
) -> NotificationOutbox:
    existing = await session.scalar(
        select(NotificationOutbox).where(NotificationOutbox.idempotency_key == idempotency_key)
    )
    if existing:
        return existing
    notification = NotificationOutbox(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        idempotency_key=idempotency_key,
        deep_link=deep_link,
        data=data or {},
        status=NotificationStatus.PENDING,
    )
    try:
        async with session.begin_nested():
            session.add(notification)
            await session.flush()
    except IntegrityError:
        recovered = await session.scalar(
            select(NotificationOutbox).where(NotificationOutbox.idempotency_key == idempotency_key)
        )
        if recovered is None:
            raise
        return recovered
    return notification


async def deliver_pending_notifications(
    session: AsyncSession,
    provider: NotificationProvider,
    *,
    limit: int = 100,
) -> tuple[int, int]:
    now = datetime.now(UTC)
    notifications = list(
        (
            await session.scalars(
                select(NotificationOutbox)
                .where(
                    NotificationOutbox.status == NotificationStatus.PENDING,
                    NotificationOutbox.next_attempt_at <= now,
                )
                .order_by(NotificationOutbox.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    sent = 0
    failed = 0
    for notification in notifications:
        tokens = list(
            (
                await session.scalars(
                    select(DeviceToken).where(
                        DeviceToken.user_id == notification.user_id,
                        DeviceToken.is_active.is_(True),
                    )
                )
            ).all()
        )
        try:
            for device in tokens:
                await provider.send(device.token, notification)
            notification.status = NotificationStatus.SENT
            notification.sent_at = now
            notification.last_error = None
            sent += 1
        except Exception as error:
            notification.attempts += 1
            notification.last_error = str(error)[:2_000]
            if notification.attempts >= 5:
                notification.status = NotificationStatus.FAILED
            else:
                notification.next_attempt_at = now + timedelta(
                    seconds=min(3_600, 2**notification.attempts * 15)
                )
            failed += 1
            logger.exception(
                "notification_delivery_failed",
                notification_id=str(notification.id),
                attempts=notification.attempts,
            )
    await session.commit()
    return sent, failed


async def enqueue_due_notifications(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    created = 0
    expiring = await session.scalars(
        select(Reservation).where(
            Reservation.status == ReservationStatus.ACTIVE,
            Reservation.expires_at > now,
            Reservation.expires_at <= now + timedelta(minutes=10),
        )
    )
    for reservation in expiring:
        await enqueue_notification(
            session,
            user_id=reservation.buyer_id,
            notification_type="reservation_expiring",
            title="Reservation expiring soon",
            body="Coordinate pickup or this item will return to the marketplace.",
            idempotency_key=f"reservation-expiring:{reservation.id}",
            deep_link=f"yard://reservations/{reservation.id}",
        )
        created += 1
    offers = await session.scalars(
        select(WaitlistEntry).where(
            WaitlistEntry.status == WaitlistStatus.OFFERED,
            WaitlistEntry.offer_expires_at > now,
        )
    )
    for offer in offers:
        await enqueue_notification(
            session,
            user_id=offer.buyer_id,
            notification_type="waitlist_offer",
            title="An item is available",
            body="Your waitlist offer is ready. Claim it before it expires.",
            idempotency_key=f"waitlist-offer:{offer.id}",
            deep_link=f"yard://waitlist/{offer.id}",
        )
        created += 1
    pickups = (
        await session.execute(
            select(PickupSession, Reservation.buyer_id, Reservation.seller_id)
            .join(Reservation, Reservation.id == PickupSession.reservation_id)
            .where(
                PickupSession.status == PickupStatus.SCHEDULED,
                PickupSession.proposed_for > now,
                PickupSession.proposed_for <= now + timedelta(hours=1),
            )
        )
    ).all()
    for pickup, buyer_id, seller_id in pickups:
        for user_id in (buyer_id, seller_id):
            await enqueue_notification(
                session,
                user_id=user_id,
                notification_type="pickup_reminder",
                title="Pickup is coming up",
                body=f"Your pickup at {pickup.meeting_zone} is within the hour.",
                idempotency_key=f"pickup-reminder:{pickup.id}:{user_id}",
                deep_link=f"yard://reservations/{pickup.reservation_id}",
            )
            created += 1
    await session.commit()
    return created
