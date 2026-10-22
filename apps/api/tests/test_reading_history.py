import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import AccountOwner, Paper, ReadingAnswer, ResearchDocument
from app.db.models.enums import EvidenceStrength, OwnerKind
from app.documents.answers import AnswerResult
from app.documents.history import read_history, save_history
from tests.test_answer_usage import request
from tests.test_document_repository import NOW, exercise
from tests.test_document_vectors import seed


def test_history_is_bounded_and_removed_with_account(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        await seed(session, doc)
        result = AnswerResult(status="insufficient_evidence", reason="no_passages")
        for i in range(22):
            await save_history(
                session, owner.id, doc.id, request(question=f"Question {i}"), result
            )
        await session.commit()
        async with sessions() as reader:
            entries = await read_history(reader, owner.id, doc.id)
            assert len(entries) == 20
            assert all(entry.result == result for entry in entries)
        await session.execute(delete(AccountOwner).where(AccountOwner.id == owner.id))
        await session.commit()
        assert (
            await session.scalar(select(func.count()).select_from(ReadingAnswer)) == 0
        )

    asyncio.run(exercise(migrated_database_url, scenario))


@pytest.mark.skipif(
    not os.environ.get("TEST_DOCUMENT_POSTGRES_URL"),
    reason="Disposable PostgreSQL not configured",
)
def test_postgres_history_roundtrip_and_deletion():
    async def run():
        engine = create_async_engine(os.environ["TEST_DOCUMENT_POSTGRES_URL"])
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        owner_id, paper_id = uuid4(), uuid4()
        try:
            async with sessions() as session:
                owner = AccountOwner(
                    id=owner_id, kind=OwnerKind.AUTHENTICATED, auth_subject=str(uuid4())
                )
                paper = Paper(
                    id=paper_id,
                    title="History fixture",
                    normalized_title="history fixture",
                    publication_year=2026,
                    evidence_strength=list(EvidenceStrength)[0],
                    primary_source_url="https://example.org/fixture",
                    last_verified_at=NOW,
                )
                session.add_all([owner, paper])
                await session.flush()
                doc = ResearchDocument(
                    owner_id=owner_id,
                    paper_id=paper_id,
                    filename="fixture.pdf",
                    byte_size=100,
                    sha256="a" * 64,
                )
                session.add(doc)
                await session.commit()
                await seed(session, doc)
                result = AnswerResult(
                    status="insufficient_evidence", reason="no_passages"
                )
                await save_history(
                    session,
                    owner_id,
                    doc.id,
                    request(question="Private question"),
                    result,
                )
                await session.commit()
            async with sessions() as reader:
                entries = await read_history(reader, owner_id, doc.id)
                assert len(entries) == 1 and entries[0].question == "Private question"
                assert entries[0].result == result
                await reader.execute(
                    delete(AccountOwner).where(AccountOwner.id == owner_id)
                )
                await reader.commit()
                assert (
                    await reader.scalar(
                        select(func.count())
                        .select_from(ReadingAnswer)
                        .where(ReadingAnswer.owner_id == owner_id)
                    )
                    == 0
                )
        finally:
            async with sessions() as session:
                await session.execute(
                    delete(AccountOwner).where(AccountOwner.id == owner_id)
                )
                await session.execute(delete(Paper).where(Paper.id == paper_id))
                await session.commit()
            await engine.dispose()

    asyncio.run(run())
