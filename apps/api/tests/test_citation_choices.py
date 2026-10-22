import asyncio
import json

import httpx2
import pytest

from app.documents.answers import Candidate, Evidence, resolve
from app.documents.citation_choices import catalog, materialize
from tests.test_gemini_answers import envelope, provider


def payload(text="A speci\ufb01ed\n parameter grid."):
    return json.dumps(
        {
            "question": "How?",
            "excerpts": [
                {
                    "id": "p0",
                    "page": 2,
                    "start": 17,
                    "end": 17 + len(text),
                    "text": text,
                }
            ],
        }
    )


def selection(ids):
    return json.dumps(
        {
            "status": "answer",
            "claims": [{"text": "A parameter grid.", "citation_ids": ids}],
        }
    )


def test_choices_preserve_original_text_and_cover_boundaries():
    text = "x" * 1200
    _, choices = catalog(payload(text))
    assert len(choices) == 3
    assert all(len(c["quote"]) <= 500 for c in choices.values())
    source = json.loads(payload())["excerpts"]
    _, choices = catalog(payload())
    candidate = Candidate.model_validate_json(materialize(selection(["c0"]), choices))
    result = resolve(candidate, tuple(Evidence.model_validate(e) for e in source))
    citation = result[0].citations[0]
    assert citation.start == 17
    assert citation.quote == source[0]["text"]


@pytest.mark.parametrize("ids", [["forged"], ["c0", "c0"]])
def test_invalid_choices_fail(ids):
    _, choices = catalog(payload())
    with pytest.raises(ValueError):
        materialize(selection(ids), choices)


def test_model_cannot_supply_its_own_quote():
    _, choices = catalog(payload())
    raw = json.loads(selection(["c0"]))
    raw["claims"][0]["quote"] = "invented"
    with pytest.raises(ValueError):
        materialize(json.dumps(raw), choices)


def test_real_adapter_materializes_choice_ids():
    def handler(request):
        body = json.loads(request.content)
        data = json.loads(body["contents"][0]["parts"][0]["text"])
        assert (
            data["citation_choices"]["c0"]["quote"]
            == json.loads(payload())["excerpts"][0]["text"]
        )
        return httpx2.Response(200, json=envelope(json.loads(selection(["c0"]))))

    async def run():
        client = provider(handler)
        try:
            result = Candidate.model_validate_json(
                await client.generate("unused", payload())
            )
            assert (
                result.claims[0].citations[0].quote
                == json.loads(payload())["excerpts"][0]["text"]
            )
        finally:
            await client.aclose()

    asyncio.run(run())
