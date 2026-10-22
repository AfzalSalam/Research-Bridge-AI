import asyncio
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.db.models import DocumentPage
from app.documents.retrieval import PassageQuery, keywords, retrieve
from tests.test_document_repository import exercise

FIXTURE_PAGES = [
    "The method uses graph attention to classify molecular structures.",
    "Evaluation used five-fold validation. "
    "Accuracy was measured on held-out molecules.",
    "Limitations include small datasets and missing external validation.",
]


async def check_retrieval(session, sessions, owner, doc):
    with pytest.raises(AppError) as error:
        await retrieve(session, owner.id, doc.id, PassageQuery(query="method"))
    assert error.value.status_code == 409
    doc.status = "ready"
    for number, content in enumerate(FIXTURE_PAGES, 1):
        session.add(
            DocumentPage(
                document_id=doc.id,
                number=number,
                text=content,
                chunks=[{"start": 0, "end": len(content), "text": content}],
            )
        )
    await session.commit()
    with pytest.raises(AppError) as error:
        await retrieve(session, uuid4(), doc.id, PassageQuery(query="method"))
    assert error.value.status_code == 404
    for query, expected in [
        ("graph attention", 1),
        ("held-out molecules", 2),
        ("small datasets", 3),
    ]:
        result = await retrieve(session, owner.id, doc.id, PassageQuery(query=query))
        assert result.passages[0].page == expected
        for passage in result.passages:
            assert (
                FIXTURE_PAGES[passage.page - 1][passage.start : passage.end]
                == passage.text
            )
    for query in ["quantum entanglement", "the of and", "!!!"]:
        result = await retrieve(session, owner.id, doc.id, PassageQuery(query=query))
        assert result.status == "no_matches"
        assert not result.passages


def test_retrieval_ownership_citations_and_small_fixture(migrated_database_url):
    asyncio.run(exercise(migrated_database_url, check_retrieval))


def test_query_normalization_is_bounded_and_not_query_syntax():
    assert keywords('"Graph" OR graph; DROP TABLE papers --') == [
        "graph",
        "drop",
        "table",
        "papers",
    ]
    assert len(keywords(" ".join(f"term{i}" for i in range(40)))) == 24


def test_overlaps_and_invalid_offsets_are_excluded(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        doc.status = "ready"
        content = "graph attention method graph results"
        session.add(
            DocumentPage(
                document_id=doc.id,
                number=1,
                text=content,
                chunks=[
                    {"start": 0, "end": 22, "text": content[:22]},
                    {"start": 16, "end": len(content), "text": content[16:]},
                    {"start": 0, "end": 5, "text": "graph forged"},
                ],
            )
        )
        await session.commit()
        result = await retrieve(session, owner.id, doc.id, PassageQuery(query="graph"))
        assert len(result.passages) == 1
        assert result.passages[0].text == content[:22]

    asyncio.run(exercise(migrated_database_url, scenario))
