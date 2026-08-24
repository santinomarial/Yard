import asyncio
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

from botocore.client import Config  # type: ignore[import-untyped]
from botocore.session import Session  # type: ignore[import-untyped]

from app.core.config import get_settings


@dataclass(frozen=True)
class PresignedUpload:
    url: str
    headers: dict[str, str]
    expires_in_seconds: int


@dataclass(frozen=True)
class StoredObject:
    byte_size: int
    content_type: str | None


class ObjectStorage(Protocol):
    def presign_upload(self, key: str, content_type: str) -> PresignedUpload: ...

    async def head(self, key: str) -> StoredObject: ...

    async def read_prefix(self, key: str, length: int = 32) -> bytes: ...

    async def delete(self, key: str) -> None: ...


class S3ObjectStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.s3_bucket
        self.expiration = settings.upload_expiration_seconds
        session = Session()
        client_options: dict[str, Any] = {
            "service_name": "s3",
            "region_name": settings.s3_region,
            "config": Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        }
        if settings.environment != "production":
            client_options["aws_access_key_id"] = settings.s3_access_key
            client_options["aws_secret_access_key"] = settings.s3_secret_key
        public_endpoint = (
            None if settings.environment == "production" else settings.s3_public_endpoint
        )
        internal_endpoint = (
            None if settings.environment == "production" else settings.s3_internal_endpoint
        )
        self.public_client = session.create_client(endpoint_url=public_endpoint, **client_options)
        self.internal_client = session.create_client(
            endpoint_url=internal_endpoint, **client_options
        )

    def presign_upload(self, key: str, content_type: str) -> PresignedUpload:
        url = self.public_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=self.expiration,
            HttpMethod="PUT",
        )
        return PresignedUpload(
            url=url,
            headers={"Content-Type": content_type},
            expires_in_seconds=self.expiration,
        )

    async def head(self, key: str) -> StoredObject:
        response = await asyncio.to_thread(
            self.internal_client.head_object, Bucket=self.bucket, Key=key
        )
        return StoredObject(
            byte_size=int(response["ContentLength"]),
            content_type=response.get("ContentType"),
        )

    async def read_prefix(self, key: str, length: int = 32) -> bytes:
        response = await asyncio.to_thread(
            self.internal_client.get_object,
            Bucket=self.bucket,
            Key=key,
            Range=f"bytes=0-{length - 1}",
        )
        return await asyncio.to_thread(response["Body"].read)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self.internal_client.delete_object, Bucket=self.bucket, Key=key)


@lru_cache
def get_object_storage() -> ObjectStorage:
    return S3ObjectStorage()
