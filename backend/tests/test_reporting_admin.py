import uuid
from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models import (
    AdminAction,
    Conversation,
    ConversationMember,
    Listing,
    ListingStatus,
    Message,
    MessageType,
    Report,
    ReportStatus,
    User,
)


def token_headers(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


async def report_users(
    session: AsyncSession, listing: Listing
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    seller = User(id=listing.seller_id, display_name="Reported Seller")
    reporter = User(display_name="Safety Reporter")
    admin = User(display_name="Yard Moderator", is_admin=True)
    session.add_all([seller, reporter, admin])
    await session.flush()
    ids = seller.id, reporter.id, admin.id
    await session.commit()
    return ids


async def test_listing_report_takedown_and_admin_audit(
    client: AsyncClient, seeded_session: AsyncSession
) -> None:
    listing = await seeded_session.scalar(
        select(Listing).where(Listing.status == ListingStatus.ACTIVE).limit(1)
    )
    assert listing is not None
    listing_id = listing.id
    seller_id, reporter_id, admin_id = await report_users(seeded_session, listing)
    report_payload = {
        "target_type": "listing",
        "target_id": str(listing_id),
        "reason": "prohibited_item",
        "details": "The description appears to offer a prohibited item.",
    }
    created = await client.post(
        "/api/v1/reports", json=report_payload, headers=token_headers(reporter_id)
    )
    assert created.status_code == 201
    report_id = uuid.UUID(created.json()["id"])
    assert created.json()["severity"] == "high"

    duplicate = await client.post(
        "/api/v1/reports", json=report_payload, headers=token_headers(reporter_id)
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == str(report_id)
    forbidden = await client.get("/api/v1/admin/reports", headers=token_headers(reporter_id))
    assert forbidden.status_code == 403

    queue = await client.get("/api/v1/admin/reports?status=open", headers=token_headers(admin_id))
    assert queue.status_code == 200
    assert [item["id"] for item in queue.json()] == [str(report_id)]
    resolved = await client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        json={"action": "remove_listing", "notes": "Confirmed against marketplace policy."},
        headers=token_headers(admin_id),
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    listing = await seeded_session.get(Listing, listing_id)
    report = await seeded_session.get(Report, report_id)
    assert listing is not None and report is not None
    assert listing.status == ListingStatus.REMOVED
    assert report.status == ReportStatus.RESOLVED
    action = await seeded_session.scalar(
        select(AdminAction).where(AdminAction.report_id == report_id)
    )
    assert action is not None
    assert action.action_type == "remove_listing"

    user_report = await client.post(
        "/api/v1/reports",
        json={
            "target_type": "user",
            "target_id": str(seller_id),
            "reason": "scam_fraud",
        },
        headers=token_headers(reporter_id),
    )
    suspended = await client.post(
        f"/api/v1/admin/reports/{user_report.json()['id']}/resolve",
        json={"action": "suspend_user", "notes": "Confirmed coordinated scam reports."},
        headers=token_headers(admin_id),
    )
    assert suspended.status_code == 200
    assert (
        await client.get("/api/v1/auth/me", headers=token_headers(seller_id))
    ).status_code == 401


async def test_moderator_cannot_resolve_their_own_report(
    client: AsyncClient, seeded_session: AsyncSession
) -> None:
    listing = await seeded_session.scalar(
        select(Listing).where(Listing.status == ListingStatus.ACTIVE).limit(1)
    )
    assert listing is not None
    _, _, admin_id = await report_users(seeded_session, listing)
    reported = await client.post(
        "/api/v1/reports",
        json={
            "target_type": "listing",
            "target_id": str(listing.id),
            "reason": "other",
        },
        headers=token_headers(admin_id),
    )
    assert reported.status_code == 201
    resolved = await client.post(
        f"/api/v1/admin/reports/{reported.json()['id']}/resolve",
        json={"action": "dismiss"},
        headers=token_headers(admin_id),
    )
    assert resolved.status_code == 409
    assert resolved.json()["error"]["code"] == "self_review_forbidden"


async def test_only_conversation_members_can_report_a_counterpart_message(
    client: AsyncClient, seeded_session: AsyncSession
) -> None:
    listing = await seeded_session.scalar(
        select(Listing).where(Listing.status == ListingStatus.ACTIVE).limit(1)
    )
    assert listing is not None
    seller = User(id=listing.seller_id, display_name="Message Seller")
    buyer = User(display_name="Message Buyer")
    outsider = User(display_name="Message Outsider")
    seeded_session.add_all([seller, buyer, outsider])
    await seeded_session.flush()
    seller_id, buyer_id, outsider_id = seller.id, buyer.id, outsider.id
    conversation = Conversation(listing_id=listing.id, buyer_id=buyer_id)
    seeded_session.add(conversation)
    await seeded_session.flush()
    seeded_session.add_all(
        [
            ConversationMember(conversation_id=conversation.id, user_id=seller_id),
            ConversationMember(conversation_id=conversation.id, user_id=buyer_id),
        ]
    )
    message = Message(
        conversation_id=conversation.id,
        sender_id=seller_id,
        message_type=MessageType.TEXT,
        body="Suspicious message",
        created_at=datetime.now(UTC),
    )
    seeded_session.add(message)
    await seeded_session.commit()
    message_id = message.id
    payload = {
        "target_type": "message",
        "target_id": str(message_id),
        "reason": "harassment",
    }

    outsider_response = await client.post(
        "/api/v1/reports", json=payload, headers=token_headers(outsider_id)
    )
    assert outsider_response.status_code == 404
    own_message = await client.post(
        "/api/v1/reports", json=payload, headers=token_headers(seller_id)
    )
    assert own_message.status_code == 404
    member_response = await client.post(
        "/api/v1/reports", json=payload, headers=token_headers(buyer_id)
    )
    assert member_response.status_code == 201
    assert member_response.json()["target_id"] == str(message_id)
