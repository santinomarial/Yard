import asyncio
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

from botocore.session import Session  # type: ignore[import-untyped]

from app.core.config import get_settings


@dataclass(frozen=True)
class ImageModerationDecision:
    approved: bool
    provider: str
    reasons: list[str]


class ImageModerationProvider(Protocol):
    async def moderate(self, storage_key: str) -> ImageModerationDecision: ...


class DeterministicDevelopmentImageModeration:
    async def moderate(self, storage_key: str) -> ImageModerationDecision:
        return ImageModerationDecision(
            approved=True,
            provider="deterministic-development-image",
            reasons=[],
        )


class RekognitionImageModeration:
    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.s3_bucket
        session = Session()
        self.client: Any = session.create_client(
            service_name="rekognition",
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )

    async def moderate(self, storage_key: str) -> ImageModerationDecision:
        response = await asyncio.to_thread(
            self.client.detect_moderation_labels,
            Image={"S3Object": {"Bucket": self.bucket, "Name": storage_key}},
            MinConfidence=75,
        )
        reasons = sorted(
            {
                str(label["Name"])
                for label in response.get("ModerationLabels", [])
                if float(label.get("Confidence", 0)) >= 75
            }
        )
        return ImageModerationDecision(
            approved=not reasons,
            provider="aws-rekognition",
            reasons=reasons,
        )


@lru_cache
def get_image_moderation_provider() -> ImageModerationProvider:
    if get_settings().environment == "production":
        return RekognitionImageModeration()
    return DeterministicDevelopmentImageModeration()
