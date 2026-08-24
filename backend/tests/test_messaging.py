import uuid
from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models import ConversationMember, Listing, ListingStatus, User


def headers_for(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


async def test_private_conversation_messages_read_state_and_blocking(
    client: AsyncClient, seeded_session: AsyncSession
) -> None:
    listing = await seeded_session.scalar(
        select(Listing).where(Listing.status == ListingStatus.ACTIVE).limit(1)
    )
    assert listing is not None
    seller = User(
        id=listing.seller_id,
        display_name="Seller",
        harvard_email="seller@harvard.edu",
        email_verified_at=datetime.now(UTC),
    )
    buyer = User(
        display_name="Buyer",
        harvard_email="buyer-messages@harvard.edu",
        email_verified_at=datetime.now(UTC),
    )
    outsider = User(
        display_name="Outsider",
        harvard_email="outsider@harvard.edu",
        email_verified_at=datetime.now(UTC),
    )
    seeded_session.add_all([seller, buyer, outsider])
    await seeded_session.commit()

    created = await client.post(
        "/api/v1/conversations",
        json={"listing_id": str(listing.id)},
        headers=headers_for(buyer),
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    assert set(created.json()["member_ids"]) == {str(buyer.id), str(seller.id)}

    duplicate = await client.post(
        "/api/v1/conversations",
        json={"listing_id": str(listing.id)},
        headers=headers_for(buyer),
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == conversation_id

    seller_inbox = await client.get("/api/v1/conversations", headers=headers_for(seller))
    assert seller_inbox.status_code == 200
    assert seller_inbox.json()[0]["id"] == conversation_id

    sent = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"body": "  Is this still available?  "},
        headers=headers_for(buyer),
    )
    assert sent.status_code == 200
    assert sent.json()["body"] == "Is this still available?"

    history = await client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=headers_for(seller),
    )
    assert history.status_code == 200
    assert [message["body"] for message in history.json()] == ["Is this still available?"]
    hidden = await client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=headers_for(outsider),
    )
    assert hidden.status_code == 404

    marked = await client.post(
        f"/api/v1/conversations/{conversation_id}/read", headers=headers_for(seller)
    )
    assert marked.status_code == 204
    member = await seeded_session.get(ConversationMember, (uuid.UUID(conversation_id), seller.id))
    assert member is not None
    await seeded_session.refresh(member)
    assert member.last_read_at is not None

    blocked = await client.put(f"/api/v1/blocks/{buyer.id}", headers=headers_for(seller))
    assert blocked.status_code == 204
    rejected = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"body": "Following up"},
        headers=headers_for(buyer),
    )
    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "interaction_blocked"


async def test_seller_cannot_open_buyer_conversation(
    client: AsyncClient, seeded_session: AsyncSession
) -> None:
    listing = await seeded_session.scalar(
        select(Listing).where(Listing.status == ListingStatus.ACTIVE).limit(1)
    )
    assert listing is not None
    seller = User(id=listing.seller_id, display_name="Seller")
    seeded_session.add(seller)
    await seeded_session.commit()

    response = await client.post(
        "/api/v1/conversations",
        json={"listing_id": str(listing.id)},
        headers=headers_for(seller),
    )
    assert response.status_code == 404
