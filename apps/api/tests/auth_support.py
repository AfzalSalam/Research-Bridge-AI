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


def account_profile_payload(name: str = "Asha") -> dict[str, object]:
    """Explicit student input for authenticated integration test accounts."""

    return {
        "name": name,
        "program": "BTech Computer Science",
        "institution": "Research Bridge Institute",
        "graduationYear": "2027",
        "researchInterests": ["human-centred AI", "digital health"],
        "skills": ["Python", "FastAPI"],
        "projectTitle": "Clinical decision support",
        "projectSummary": (
            "Built a clinical decision support prototype that displays uncertainty "
            "and records evidence supplied by healthcare workers."
        ),
        "weeklyAvailability": "10-15 hours",
    }
