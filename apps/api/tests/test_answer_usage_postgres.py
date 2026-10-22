"""Opt-in independent-session quota races on a migrated disposable PostgreSQL DB."""

import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import AppError
from app.db.models import AccountOwner, AnswerReservation, Paper, ResearchDocument
from app.db.models.enums import EvidenceStrength, OwnerKind
from app.documents.answer_usage import reserve_answer
from tests.test_answer_usage import request
from tests.test_document_repository import NOW
from tests.test_document_vectors import seed

URL = os.environ.get("TEST_DOCUMENT_POSTGRES_URL")


@pytest.mark.skipif(not URL, reason="TEST_DOCUMENT_POSTGRES_URL not configured")
@pytest.mark.parametrize("duplicate", [False, True])
def test_independent_transactions_reserve_once(duplicate):
    async def run():
        assert URL and URL.startswith("postgresql+asyncpg://")
        engine = create_async_engine(URL)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        owner_id = uuid4()
        paper_id = uuid4()
        try:
            async with sessions() as session:
                owner = AccountOwner(
                    id=owner_id, kind=OwnerKind.AUTHENTICATED, auth_subject=str(uuid4())
                )
                paper = Paper(
                    id=paper_id,
                    title="Quota race",
                    normalized_title="quota race",
                    publication_year=2026,
                    evidence_strength=list(EvidenceStrength)[0],
                    primary_source_url="https://example.org/fixture",
                    last_verified_at=NOW,
                )
                session.add_all([owner, paper])
                await session.flush()
                doc = ResearchDocument(
                    owner_id=owner.id,
                    paper_id=paper.id,
                    filename="fixture.pdf",
                    byte_size=100,
                    sha256="a" * 64,
                )
                session.add(doc)
                await session.commit()
                await seed(session, doc)
            req = request()
            gate = asyncio.Event()

            async def reserve(req):
                async with sessions() as session:
                    await gate.wait()
                    try:
                        await reserve_answer(
                            session,
                            owner_id,
                            doc.id,
                            req,
                            daily_call_limit=6 if duplicate else 3,
                        )
                        await session.commit()
                        return "reserved"
                    except AppError as exc:
                        await session.rollback()
                        return exc.code

            tasks = [
                asyncio.create_task(reserve(req)),
                asyncio.create_task(reserve(req if duplicate else request())),
            ]
            gate.set()
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=15)
            assert sorted(results) == sorted(
                [
                    "reserved",
                    "answer_request_used" if duplicate else "answer_daily_quota",
                ]
            )
            async with sessions() as session:
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(AnswerReservation)
                        .where(AnswerReservation.owner_id == owner_id)
                    )
                    == 1
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
