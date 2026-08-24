import time
import uuid

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.api.router import api_router
from app.core.config import get_settings
from app.core.rate_limit import RedisRateLimiter

settings = get_settings()
logger = structlog.get_logger()
rate_limiter = RedisRateLimiter(Redis.from_url(settings.redis_url), settings)


def secure_response(response: Response, request_id: str) -> Response:
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


app = FastAPI(
    title="Yard API",
    version="0.1.0",
    description="Authoritative marketplace API for Yard.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
)


@app.exception_handler(HTTPException)
async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        error = exc.detail
    else:
        error = {"code": "http_error", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": error})


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "invalid_request",
                "message": "The request could not be validated.",
                "details": exc.errors(),
            }
        },
    )


@app.middleware("http")
async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
    supplied_request_id = request.headers.get("X-Request-ID")
    try:
        request_id = (
            str(uuid.UUID(supplied_request_id)) if supplied_request_id else str(uuid.uuid4())
        )
    except ValueError:
        request_id = str(uuid.uuid4())
    started = time.perf_counter()
    request.state.request_started_at = time.time()
    content_length = request.headers.get("Content-Length")
    try:
        request_bytes = int(content_length) if content_length else 0
    except ValueError:
        request_bytes = settings.max_request_bytes + 1
    if request_bytes > settings.max_request_bytes:
        return secure_response(
            JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "request_too_large",
                        "message": "This request is too large.",
                    }
                },
            ),
            request_id,
        )
    retry_after = await rate_limiter.retry_after(request)
    if retry_after is not None:
        return secure_response(
            JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Too many requests. Try again shortly.",
                    }
                },
            ),
            request_id,
        )
    response = await call_next(request)
    secure_response(response, request_id)
    logger.info(
        "http_request",
        request_id=request_id,
        route=request.url.path,
        method=request.method,
        status=response.status_code,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    return response


app.include_router(api_router, prefix=settings.api_prefix)
