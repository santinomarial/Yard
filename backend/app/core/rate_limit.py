import hashlib
from dataclasses import dataclass

import structlog
from fastapi import Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import Settings

logger = structlog.get_logger()


@dataclass(frozen=True)
class RateLimit:
    requests: int
    window_seconds: int


def policy_for(request: Request) -> RateLimit | None:
    path = request.url.path
    if request.method == "GET":
        return RateLimit(300, 60)
    if path.endswith("/auth/development") or path.endswith("/auth/apple"):
        return RateLimit(10, 60)
    if "/auth/verification/" in path:
        return RateLimit(10, 3_600)
    if path.endswith("/auth/review-access"):
        return RateLimit(5, 3_600)
    if path.endswith("/reservations"):
        return RateLimit(30, 60)
    if "/messages" in path:
        return RateLimit(60, 60)
    if path.endswith("/reports"):
        return RateLimit(20, 3_600)
    return RateLimit(120, 60)


def client_identifier(request: Request, settings: Settings) -> str:
    peer = request.client.host if request.client else "unknown"
    if peer in settings.trusted_proxy_ips:
        forwarded = request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
        if forwarded:
            peer = forwarded
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        digest = hashlib.sha256(authorization.removeprefix("Bearer ").encode()).hexdigest()[:24]
        return f"token:{digest}"
    return f"ip:{peer}"


class RedisRateLimiter:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def retry_after(self, request: Request) -> int | None:
        if not self.settings.rate_limit_enabled:
            return None
        policy = policy_for(request)
        if policy is None:
            return None
        identifier = client_identifier(request, self.settings)
        bucket = int(request.state.request_started_at // policy.window_seconds)
        key = f"yard:rate:{identifier}:{request.method}:{request.url.path}:{bucket}"
        try:
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, policy.window_seconds + 1)
        except RedisError:
            logger.exception("rate_limiter_unavailable")
            if self.settings.environment == "production":
                return policy.window_seconds
            return None
        if count <= policy.requests:
            return None
        return policy.window_seconds - (
            int(request.state.request_started_at) % policy.window_seconds
        )
