from typing import Any

import httpx
import jwt
from jwt import InvalidTokenError, PyJWK


class AppleTokenError(ValueError):
    pass


class AppleIdentityTokenVerifier:
    issuer = "https://appleid.apple.com"
    keys_url = "https://appleid.apple.com/auth/keys"

    def __init__(self, audience: str) -> None:
        self.audience = audience

    async def verify(self, identity_token: str) -> str:
        try:
            header = jwt.get_unverified_header(identity_token)
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(self.keys_url)
                response.raise_for_status()
            matching_key: dict[str, Any] | None = next(
                (key for key in response.json()["keys"] if key.get("kid") == header.get("kid")),
                None,
            )
            if matching_key is None:
                raise AppleTokenError("Unknown Apple signing key")
            claims = jwt.decode(
                identity_token,
                key=PyJWK.from_dict(matching_key).key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
            )
            subject = claims.get("sub")
            if not isinstance(subject, str) or not subject:
                raise AppleTokenError("Apple subject is missing")
            return subject
        except (httpx.HTTPError, InvalidTokenError, KeyError, TypeError) as error:
            raise AppleTokenError("Apple identity token is invalid") from error
