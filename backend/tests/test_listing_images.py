import uuid
from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.main import app
from app.models import Category, Listing, ListingImageStatus, User
from app.services.image_moderation import (
    ImageModerationDecision,
    get_image_moderation_provider,
)
from app.services.object_storage import (
    PresignedUpload,
    StoredObject,
    get_object_storage,
)


class FakeStorage:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def presign_upload(self, key: str, content_type: str) -> PresignedUpload:
        return PresignedUpload(
            url=f"https://uploads.test/{key}",
            headers={"Content-Type": content_type},
            expires_in_seconds=900,
        )

    async def head(self, key: str) -> StoredObject:
        return StoredObject(byte_size=1024, content_type="image/jpeg")

    async def read_prefix(self, key: str, length: int = 32) -> bytes:
        return b"\xff\xd8\xff" + bytes(length - 3)

    async def delete(self, key: str) -> None:
        self.deleted.append(key)


class ApprovingModerator:
    async def moderate(self, storage_key: str) -> ImageModerationDecision:
        return ImageModerationDecision(approved=True, provider="test-image-moderation", reasons=[])


async def test_presigned_image_upload_moderation_and_publish(
    client: AsyncClient, seeded_session: AsyncSession
) -> None:
    seller = User(
        display_name="Photo Seller",
        harvard_email="photo-seller@harvard.edu",
        email_verified_at=datetime.now(UTC),
    )
    other = User(display_name="Other Seller", email_verified_at=datetime.now(UTC))
    seeded_session.add_all([seller, other])
    await seeded_session.flush()
    seller_id, other_id = seller.id, other.id
    await seeded_session.commit()
    category_id = await seeded_session.scalar(select(Category.id).limit(1))
    assert category_id is not None
    seller_headers = {"Authorization": f"Bearer {create_access_token(seller_id)}"}
    other_headers = {"Authorization": f"Bearer {create_access_token(other_id)}"}
    storage = FakeStorage()
    app.dependency_overrides[get_object_storage] = lambda: storage
    app.dependency_overrides[get_image_moderation_provider] = ApprovingModerator

    created = await client.post(
        "/api/v1/listings",
        json={
            "title": "Desk lamp",
            "description": "Warm adjustable reading lamp.",
            "category_id": str(category_id),
            "price_cents": 1500,
            "is_free": False,
            "condition": "good",
            "pickup_zone": "Harvard Square",
        },
        headers=seller_headers,
    )
    assert created.status_code == 201
    listing_id = created.json()["id"]
    assert created.json()["images"] == []

    unauthorized = await client.post(
        f"/api/v1/listings/{listing_id}/images/uploads",
        json={"content_type": "image/jpeg", "byte_size": 1024},
        headers=other_headers,
    )
    assert unauthorized.status_code == 404
    upload = await client.post(
        f"/api/v1/listings/{listing_id}/images/uploads",
        json={"content_type": "image/jpeg", "byte_size": 1024},
        headers=seller_headers,
    )
    assert upload.status_code == 201
    image_id = upload.json()["image"]["id"]
    assert upload.json()["upload_url"].startswith("https://uploads.test/listings/")
    assert upload.json()["required_headers"] == {"Content-Type": "image/jpeg"}

    pending_submit = await client.post(
        f"/api/v1/listings/{listing_id}/submit", headers=seller_headers
    )
    assert pending_submit.status_code == 409
    assert pending_submit.json()["error"]["code"] == "image_moderation_pending"

    completed = await client.post(
        f"/api/v1/listings/{listing_id}/images/{image_id}/complete",
        headers=seller_headers,
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == ListingImageStatus.APPROVED.value
    assert completed.json()["url"].endswith(f"/listings/{listing_id}/{image_id}.jpg")

    published = await client.post(f"/api/v1/listings/{listing_id}/submit", headers=seller_headers)
    assert published.status_code == 200
    assert published.json()["status"] == "active"
    assert published.json()["image_url"] == completed.json()["url"]
    assert len(published.json()["images"]) == 1

    locked_delete = await client.delete(
        f"/api/v1/listings/{listing_id}/images/{image_id}", headers=seller_headers
    )
    assert locked_delete.status_code == 409
    listing = await seeded_session.get(Listing, uuid.UUID(listing_id))
    assert listing is not None
