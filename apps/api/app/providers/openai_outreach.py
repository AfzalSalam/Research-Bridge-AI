from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

import httpx2
from pydantic import ValidationError

from app.outreach.drafting import (
    PROMPT_VERSION,
    DraftProviderError,
    OutreachComposition,
    OutreachEvidencePackage,
)

_TRANSIENT_STATUSES = {429, 500, 502, 503, 504}
_DEVELOPER_PROMPT = """You write one concise academic outreach email composition.
Use only facts in the supplied evidence package. Never invent or infer an academic
title, current institution, contact detail, lab opening, availability, funding,
supervision history, paper method, paper result, acceptance chance, or response
chance. Refer to every selected paper exactly once using its exact paperId. For a
title-only paper, mention only its title, year, and listed topics and explicitly
avoid claims about methods or findings. Return only the required structured
fields. Do not include a greeting or signoff; the application adds those
deterministically. Phrase possible student work as a respectful question."""


class OpenAIOutreachProvider:
    """Narrow Responses API adapter for strict, evidence-bounded prose."""

    name = "OpenAI"

    def __init__(
        self,
        client: httpx2.AsyncClient,
        *,
        api_key: str,
        model: str,
        max_attempts: int,
        backoff_base_seconds: float,
        backoff_cap_seconds: float,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self.model = model
        self._max_attempts = max_attempts
        self._backoff_base_seconds = backoff_base_seconds
        self._backoff_cap_seconds = backoff_cap_seconds
        self._sleep = sleep

    async def generate(self, evidence: OutreachEvidencePackage) -> OutreachComposition:
        response = await self._post(_request_payload(evidence, model=self.model))
        try:
            payload = response.json()
        except ValueError as error:
            raise DraftProviderError("invalid-provider-output") from error
        output_text = _output_text(payload)
        try:
            return OutreachComposition.model_validate_json(output_text)
        except (ValidationError, ValueError) as error:
            raise DraftProviderError("invalid-provider-output") from error

    async def _post(self, payload: dict[str, Any]) -> httpx2.Response:
        for attempt in range(self._max_attempts):
            try:
                response = await self._client.post(
                    "/responses",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            except httpx2.TransportError as error:
                if attempt + 1 < self._max_attempts:
                    await self._sleep(self._backoff_delay(attempt))
                    continue
                raise DraftProviderError("provider-unavailable") from error

            if response.status_code in _TRANSIENT_STATUSES:
                if attempt + 1 < self._max_attempts:
                    await self._sleep(self._backoff_delay(attempt))
                    continue
                raise DraftProviderError("provider-unavailable")
            if response.status_code in {401, 403}:
                raise DraftProviderError("provider-unavailable")
            if response.status_code >= 400:
                raise DraftProviderError("provider-refused")
            return response

        raise AssertionError("OpenAI retry loop exhausted without a result")

    def _backoff_delay(self, attempt: int) -> float:
        return float(
            min(
                self._backoff_base_seconds * (2**attempt),
                self._backoff_cap_seconds,
            )
        )


def _request_payload(
    evidence: OutreachEvidencePackage, *, model: str
) -> dict[str, Any]:
    user_payload = {
        "promptVersion": PROMPT_VERSION,
        "recipient": {
            "displayName": evidence.mentor.display_name,
            "academicTitle": None,
            "currentInstitution": None,
            "contact": None,
            "availability": "unknown",
        },
        "studentFacts": [
            {"key": fact.key, "label": fact.label, "value": fact.value}
            for fact in evidence.student_facts
        ],
        "selectedPapers": [
            {
                "paperId": str(paper.id),
                "title": paper.title,
                "year": paper.publication_year,
                "venue": paper.venue,
                "topics": [topic.display_name for topic in paper.topics],
                "evidenceStrength": paper.evidence_strength,
                "validatedAbstract": paper.abstract_excerpt,
            }
            for paper in evidence.papers
        ],
    }
    schema = OutreachComposition.model_json_schema()
    return {
        "model": model,
        "store": False,
        "reasoning": {"effort": "low"},
        "max_output_tokens": 1600,
        "input": [
            {
                "role": "developer",
                "content": [{"type": "input_text", "text": _DEVELOPER_PROMPT}],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(user_payload, ensure_ascii=False),
                    }
                ],
            },
        ],
        "text": {
            "verbosity": "low",
            "format": {
                "type": "json_schema",
                "name": "research_bridge_outreach",
                "strict": True,
                "schema": schema,
            },
        },
    }


def _output_text(payload: object) -> str:
    if not isinstance(payload, dict):
        raise DraftProviderError("invalid-provider-output")
    if payload.get("status") == "incomplete":
        raise DraftProviderError("provider-unavailable")
    output = payload.get("output")
    if not isinstance(output, list):
        raise DraftProviderError("invalid-provider-output")
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "refusal":
                raise DraftProviderError("provider-refused")
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                return str(part["text"])
    raise DraftProviderError("invalid-provider-output")
