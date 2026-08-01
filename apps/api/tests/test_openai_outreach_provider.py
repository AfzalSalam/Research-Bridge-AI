import asyncio
import json

import httpx2
import pytest

from app.fixtures.demo import fresh_profile
from app.outreach.drafting import (
    CompositionPaperConnection,
    DraftProviderError,
    OutreachComposition,
    build_evidence_package,
)
from app.providers.openai_outreach import OpenAIOutreachProvider
from app.relevance.mentor import RelevanceWeights, derive_candidates
from app.services.mentor_discovery import _candidate_response
from scripts.evaluate_mentor_relevance import (
    FIXTURE_PATH,
    EvaluationFixture,
)


def evidence_package():
    evaluation = EvaluationFixture.model_validate_json(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )
    case = evaluation.cases[0]
    candidate = derive_candidates(
        query=case.query,
        query_kind=case.query_kind,
        papers=case.papers,
        profile=fresh_profile(),
        evaluation_year=evaluation.evaluation_year,
        weights=RelevanceWeights(),
    ).candidates[0]
    response = _candidate_response(candidate)
    return build_evidence_package(
        mentor=response,
        papers=response.supporting_papers[:1],
        profile=fresh_profile(),
    )


def valid_composition() -> OutreachComposition:
    evidence = evidence_package()
    return OutreachComposition(
        subject="Question about evidence-centred research",
        introduction=(
            "I am Aarav Demo, a BTech Computer Science student interested in "
            "evidence-aware research software."
        ),
        student_fact_keys=["profile.name", "profile.program"],
        paper_connections=[
            CompositionPaperConnection(
                paper_id=evidence.papers[0].id,
                text=(
                    "I appreciated the paper's careful framing of evidence and its "
                    "connection to responsible decision support."
                ),
            )
        ],
        ask=(
            "Would you be open to a brief conversation about whether a focused "
            "student contribution could be useful?"
        ),
    )


def build_provider(
    transport: httpx2.AsyncBaseTransport,
    *,
    sleep: object | None = None,
) -> tuple[httpx2.AsyncClient, OpenAIOutreachProvider]:
    client = httpx2.AsyncClient(
        base_url="https://api.openai.com/v1", transport=transport
    )

    async def no_sleep(_: float) -> None:
        return None

    return client, OpenAIOutreachProvider(
        client,
        api_key="secret-test-key",
        model="test-model",
        max_attempts=2,
        backoff_base_seconds=0.5,
        backoff_cap_seconds=2,
        sleep=sleep if callable(sleep) else no_sleep,
    )


def test_provider_uses_store_false_and_strict_structured_output() -> None:
    seen: list[httpx2.Request] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": valid_composition().model_dump_json(),
                            }
                        ],
                    }
                ],
            },
        )

    async def run() -> OutreachComposition:
        client, provider = build_provider(httpx2.MockTransport(handler))
        try:
            return await provider.generate(evidence_package())
        finally:
            await client.aclose()

    result = asyncio.run(run())
    assert result.subject == "Question about evidence-centred research"
    assert len(seen) == 1
    assert seen[0].url.path == "/v1/responses"
    assert seen[0].headers["Authorization"] == "Bearer secret-test-key"
    payload = json.loads(seen[0].content)
    assert payload["store"] is False
    assert payload["reasoning"] == {"effort": "low"}
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True


def test_transient_failures_retry_with_a_bounded_delay() -> None:
    attempts = 0
    delays: list[float] = []

    async def handler(_: httpx2.Request) -> httpx2.Response:
        nonlocal attempts
        attempts += 1
        return httpx2.Response(503)

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    async def run() -> DraftProviderError:
        client, provider = build_provider(
            httpx2.MockTransport(handler), sleep=record_sleep
        )
        try:
            with pytest.raises(DraftProviderError) as captured:
                await provider.generate(evidence_package())
            return captured.value
        finally:
            await client.aclose()

    error = asyncio.run(run())
    assert attempts == 2
    assert delays == [0.5]
    assert error.reason == "provider-unavailable"
    assert "secret-test-key" not in str(error)


@pytest.mark.parametrize(
    ("response_payload", "reason"),
    [
        (
            {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "refusal", "refusal": "No"}],
                    }
                ],
            },
            "provider-refused",
        ),
        (
            {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "not-json"}],
                    }
                ],
            },
            "invalid-provider-output",
        ),
    ],
)
def test_refusal_and_invalid_output_are_secret_safe_fallback_reasons(
    response_payload: dict[str, object], reason: str
) -> None:
    async def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=response_payload)

    async def run() -> DraftProviderError:
        client, provider = build_provider(httpx2.MockTransport(handler))
        try:
            with pytest.raises(DraftProviderError) as captured:
                await provider.generate(evidence_package())
            return captured.value
        finally:
            await client.aclose()

    error = asyncio.run(run())
    assert error.reason == reason
    assert "secret-test-key" not in str(error)
