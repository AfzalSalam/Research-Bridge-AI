"""Small deterministic token verifier for API tests without a provider account."""

from app.auth.contracts import VerifiedIdentity
from app.auth.supabase import AccessTokenInvalidError


class StaticAccessTokenVerifier:
    """Map test bearer values to stable provider subjects."""

    def __init__(self, token_subjects: dict[str, str]) -> None:
        self._token_subjects = token_subjects

    async def verify_access_token(self, token: str) -> VerifiedIdentity:
        subject = self._token_subjects.get(token)
        if subject is None:
            raise AccessTokenInvalidError
        return VerifiedIdentity(subject=subject)
