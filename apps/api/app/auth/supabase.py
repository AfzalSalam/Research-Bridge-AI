"""Supabase JWT verification using the configured project's JWKS endpoint."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping

import httpx2
import jwt
from jwt.exceptions import DecodeError, InvalidTokenError, PyJWKError

from app.auth.contracts import VerifiedIdentity

_ALLOWED_ALGORITHMS = frozenset(
    {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "EdDSA"}
)
_MAX_ACCESS_TOKEN_LENGTH = 8_192


class AccessTokenInvalidError(Exception):
    """The bearer token is missing required claims or cannot be verified."""


class AuthenticationProviderUnavailableError(Exception):
    """The configured identity provider could not supply verification keys."""


class FixedAccessTokenVerifier:
    """Strict test-only verifier used by the isolated browser E2E process."""

    def __init__(self, *, token: str, subject: str) -> None:
        self._token = token
        self._subject = subject

    async def verify_access_token(self, token: str) -> VerifiedIdentity:
        if token != self._token:
            raise AccessTokenInvalidError
        return VerifiedIdentity(subject=self._subject)


class SupabaseTokenVerifier:
    """Verify asymmetric Supabase access tokens against cached project JWKS keys."""

    def __init__(
        self,
        *,
        http_client: httpx2.AsyncClient,
        audience: str,
        issuer: str,
        jwks_cache_ttl_seconds: int,
    ) -> None:
        self._http_client = http_client
        self._audience = audience
        self._issuer = issuer
        self._jwks_cache_ttl_seconds = jwks_cache_ttl_seconds
        self._keys: dict[str, jwt.PyJWK] = {}
        self._keys_refreshed_at: float | None = None
        self._refresh_lock = asyncio.Lock()

    async def verify_access_token(self, token: str) -> VerifiedIdentity:
        if not token or len(token) > _MAX_ACCESS_TOKEN_LENGTH:
            raise AccessTokenInvalidError
        try:
            header = jwt.get_unverified_header(token)
        except DecodeError as error:
            raise AccessTokenInvalidError from error

        key_id = header.get("kid")
        algorithm = header.get("alg")
        if (
            not isinstance(key_id, str)
            or not key_id
            or not isinstance(algorithm, str)
            or algorithm not in _ALLOWED_ALGORITHMS
        ):
            raise AccessTokenInvalidError

        key = await self._get_key(key_id)
        if key.algorithm_name != algorithm:
            raise AccessTokenInvalidError
        try:
            claims = jwt.decode(
                token,
                key=key.key,
                algorithms=[algorithm],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["aud", "exp", "iat", "sub"]},
            )
        except InvalidTokenError as error:
            raise AccessTokenInvalidError from error

        subject = claims.get("sub")
        if (
            not isinstance(subject, str)
            or not subject.strip()
            or len(subject) > 255
            or claims.get("role") != "authenticated"
        ):
            raise AccessTokenInvalidError
        return VerifiedIdentity(subject=subject)

    async def _get_key(self, key_id: str) -> jwt.PyJWK:
        if not self._cache_is_fresh():
            await self._refresh_keys()
        key = self._keys.get(key_id)
        if key is None:
            raise AccessTokenInvalidError
        return key

    def _cache_is_fresh(self) -> bool:
        return (
            self._keys_refreshed_at is not None
            and time.monotonic() - self._keys_refreshed_at
            < self._jwks_cache_ttl_seconds
        )

    async def _refresh_keys(self) -> None:
        async with self._refresh_lock:
            if self._cache_is_fresh():
                return
            try:
                response = await self._http_client.get("/auth/v1/.well-known/jwks.json")
                response.raise_for_status()
                payload = response.json()
            except (httpx2.HTTPError, ValueError) as error:
                raise AuthenticationProviderUnavailableError from error

            if not isinstance(payload, Mapping):
                raise AuthenticationProviderUnavailableError
            raw_keys = payload.get("keys")
            if not isinstance(raw_keys, list):
                raise AuthenticationProviderUnavailableError

            parsed_keys: dict[str, jwt.PyJWK] = {}
            for raw_key in raw_keys:
                if not isinstance(raw_key, Mapping):
                    continue
                key_id = raw_key.get("kid")
                algorithm = raw_key.get("alg")
                if (
                    not isinstance(key_id, str)
                    or not key_id
                    or not isinstance(algorithm, str)
                    or algorithm not in _ALLOWED_ALGORITHMS
                ):
                    continue
                try:
                    parsed_key = jwt.PyJWK.from_dict(dict(raw_key))
                except PyJWKError:
                    continue
                if parsed_key.algorithm_name == algorithm:
                    parsed_keys[key_id] = parsed_key

            if not parsed_keys:
                raise AuthenticationProviderUnavailableError
            self._keys = parsed_keys
            self._keys_refreshed_at = time.monotonic()
