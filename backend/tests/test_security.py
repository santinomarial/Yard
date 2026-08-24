import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.core.config import Settings
from app.core.rate_limit import client_identifier, policy_for


def request(path: str, method: str = "POST", headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (name.lower().encode(), value.encode()) for name, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": raw_headers,
            "client": ("10.0.0.8", 1234),
            "scheme": "https",
            "server": ("test", 443),
            "query_string": b"",
        }
    )


def test_sensitive_routes_have_tighter_rate_limits() -> None:
    verification = policy_for(request("/api/v1/auth/verification/request"))
    messages = policy_for(request("/api/v1/conversations/id/messages"))

    assert verification is not None and verification.requests == 10
    assert messages is not None and messages.requests == 60


def test_forwarded_ip_is_trusted_only_from_configured_proxy() -> None:
    incoming = request("/api/v1/listings", headers={"X-Forwarded-For": "203.0.113.9"})
    default = client_identifier(incoming, Settings(rate_limit_enabled=False))
    trusted = client_identifier(
        incoming,
        Settings(rate_limit_enabled=False, trusted_proxy_ips=["10.0.0.8"]),
    )

    assert default == "ip:10.0.0.8"
    assert trusted == "ip:203.0.113.9"


def test_production_rejects_default_secrets_and_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", cors_origins=["*"])
