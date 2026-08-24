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
    listing_id = listing.id
    seller_id = seller.id
    buyer_id = buyer.id
    seller_headers = headers_for(seller)
    buyer_headers = headers_for(buyer)
    outsider_headers = headers_for(outsider)

    created = await client.post(
        "/api/v1/conversations",
        json={"listing_id": str(listing_id)},
        headers=buyer_headers,
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    assert set(created.json()["member_ids"]) == {str(buyer_id), str(seller_id)}

    duplicate = await client.post(
        "/api/v1/conversations",
        json={"listing_id": str(listing_id)},
        headers=buyer_headers,
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == conversation_id

    seller_inbox = await client.get("/api/v1/conversations", headers=seller_headers)
    assert seller_inbox.status_code == 200
    assert seller_inbox.json()[0]["id"] == conversation_id

    sent = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"body": "  Is this still available?  "},
        headers=buyer_headers,
    )
    assert sent.status_code == 200
    assert sent.json()["body"] == "Is this still available?"

    history = await client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=seller_headers,
    )
    assert history.status_code == 200
    assert [message["body"] for message in history.json()] == ["Is this still available?"]
    hidden = await client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=outsider_headers,
    )
    assert hidden.status_code == 404

    marked = await client.post(
        f"/api/v1/conversations/{conversation_id}/read", headers=seller_headers
    )
    assert marked.status_code == 204
    member = await seeded_session.get(ConversationMember, (uuid.UUID(conversation_id), seller_id))
    assert member is not None
    await seeded_session.refresh(member)
    assert member.last_read_at is not None

    saved = await client.put(f"/api/v1/saved/{listing_id}", headers=buyer_headers)
    assert saved.status_code == 204

    blocked = await client.put(f"/api/v1/blocks/{buyer_id}", headers=seller_headers)
    assert blocked.status_code == 204
    rejected = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"body": "Following up"},
        headers=buyer_headers,
    )
    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "interaction_blocked"

    reopened = await client.post(
        "/api/v1/conversations",
        json={"listing_id": str(listing_id)},
        headers=buyer_headers,
    )
    reserved = await client.post(
        "/api/v1/reservations",
        json={"listing_id": str(listing_id), "idempotency_key": "blocked-reservation"},
        headers=buyer_headers,
    )
    assert reopened.status_code == 403
    assert reopened.json()["error"]["code"] == "interaction_blocked"
    assert reserved.status_code == 403
    assert reserved.json()["error"]["code"] == "interaction_blocked"

    anonymous_detail = await client.get(f"/api/v1/listings/{listing_id}")
    hidden_detail = await client.get(f"/api/v1/listings/{listing_id}", headers=buyer_headers)
    hidden_browse = await client.get("/api/v1/listings", headers=buyer_headers)
    hidden_saved = await client.get("/api/v1/saved", headers=buyer_headers)
    assert anonymous_detail.status_code == 200
    assert hidden_detail.status_code == 404
    assert str(listing_id) not in {item["id"] for item in hidden_browse.json()["items"]}
    assert str(listing_id) not in {item["id"] for item in hidden_saved.json()}


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
