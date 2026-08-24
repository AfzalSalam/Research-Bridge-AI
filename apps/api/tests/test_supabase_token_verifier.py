import asyncio
import json
from datetime import UTC, datetime, timedelta

import httpx2
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.auth.supabase import AccessTokenInvalidError, SupabaseTokenVerifier

_AUDIENCE = "authenticated"
_ISSUER = "https://project-ref.supabase.co/auth/v1"
_SUBJECT = "554e78f8-71c7-4e9f-afc6-bc640114da2b"


def _token(
    private_key: rsa.RSAPrivateKey,
    *,
    audience: str = _AUDIENCE,
    expires_at: datetime | None = None,
    issuer: str = _ISSUER,
    role: str = "authenticated",
) -> str:
    issued_at = datetime.now(UTC)
    return jwt.encode(
        {
            "aud": audience,
            "exp": expires_at or issued_at + timedelta(minutes=5),
            "iat": issued_at,
            "iss": issuer,
            "role": role,
            "sub": _SUBJECT,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "current-signing-key"},
    )


def _public_jwk(private_key: rsa.RSAPrivateKey) -> dict[str, object]:
    public_key = private_key.public_key()
    raw = RSAAlgorithm.to_jwk(public_key)
    jwk = json.loads(raw)
    jwk.update({"alg": "RS256", "kid": "current-signing-key", "use": "sig"})
    return jwk


def test_supabase_verifier_checks_signature_claims_and_caches_jwks() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    requests = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal requests
        requests += 1
        assert request.url.path == "/auth/v1/.well-known/jwks.json"
        return httpx2.Response(200, json={"keys": [_public_jwk(private_key)]})

    async def run() -> None:
        async with httpx2.AsyncClient(
            base_url="https://project-ref.supabase.co",
            transport=httpx2.MockTransport(handler),
        ) as client:
            verifier = SupabaseTokenVerifier(
                http_client=client,
                audience=_AUDIENCE,
                issuer=_ISSUER,
                jwks_cache_ttl_seconds=600,
            )
            identity = await verifier.verify_access_token(_token(private_key))
            second_identity = await verifier.verify_access_token(_token(private_key))

        assert identity.subject == _SUBJECT
        assert second_identity.subject == _SUBJECT

    asyncio.run(run())
    assert requests == 1


@pytest.mark.parametrize(
    ("token_kwargs"),
    [
        {"expires_at": datetime.now(UTC) - timedelta(seconds=1)},
        {"issuer": "https://attacker.example/auth/v1"},
        {"role": "anon"},
    ],
)
def test_supabase_verifier_rejects_invalid_or_unprivileged_claims(
    token_kwargs: dict[str, object],
) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"keys": [_public_jwk(private_key)]})

    async def run() -> None:
        async with httpx2.AsyncClient(
            base_url="https://project-ref.supabase.co",
            transport=httpx2.MockTransport(handler),
        ) as client:
            verifier = SupabaseTokenVerifier(
                http_client=client,
                audience=_AUDIENCE,
                issuer=_ISSUER,
                jwks_cache_ttl_seconds=600,
            )
            with pytest.raises(AccessTokenInvalidError):
                await verifier.verify_access_token(_token(private_key, **token_kwargs))

    asyncio.run(run())
