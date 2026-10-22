"""Opt-in: migrated disposable PostgreSQL database; fixtures roll back."""

import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import AccountOwner, Paper, ResearchDocument
from app.db.models.enums import EvidenceStrength, OwnerKind
from tests.test_document_indexing import check_indexing
from tests.test_document_repository import NOW
from tests.test_document_retrieval import check_retrieval
from tests.test_document_semantic import check_query_budget
from tests.test_document_vectors import check_vectors
from tests.test_gemini import check_gemini_binding

URL = os.environ.get("TEST_DOCUMENT_POSTGRES_URL")


@pytest.mark.skipif(not URL, reason="TEST_DOCUMENT_POSTGRES_URL not configured")
def test_postgresql_passage_retrieval():
    async def run():
        assert URL and URL.startswith("postgresql+asyncpg://")
        engine = create_async_engine(URL)
        try:
            async with engine.connect() as connection:
                transaction = await connection.begin()
                try:
                    assert await connection.scalar(
                        text(
                            "SELECT to_regclass('ix_document_pages_search') IS NOT NULL"
                        )
                    )
                    sessions = async_sessionmaker(
                        connection,
                        expire_on_commit=False,
                        join_transaction_mode="create_savepoint",
                    )
                    async with sessions() as session:
                        owner = AccountOwner(
                            kind=OwnerKind.AUTHENTICATED, auth_subject=str(uuid4())
                        )
                        paper = Paper(
                            title="Retrieval fixture",
                            normalized_title="fixture",
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
                        await check_retrieval(session, sessions, owner, doc)
                        other = ResearchDocument(
                            owner_id=owner.id,
                            paper_id=paper.id,
                            filename="vector-fixture.pdf",
                            byte_size=100,
                            sha256="b" * 64,
                        )
                        session.add(other)
                        await session.commit()
                        await check_vectors(session, sessions, owner, other)
                        indexed = ResearchDocument(
                            owner_id=owner.id,
                            paper_id=paper.id,
                            filename="index-fixture.pdf",
                            byte_size=100,
                            sha256="c" * 64,
                        )
                        session.add(indexed)
                        await session.commit()
                        await check_indexing(session, sessions, owner, indexed)
                        queried = ResearchDocument(
                            owner_id=owner.id,
                            paper_id=paper.id,
                            filename="query-fixture.pdf",
                            byte_size=100,
                            sha256="d" * 64,
                        )
                        session.add(queried)
                        await session.commit()
                        await check_query_budget(session, sessions, owner, queried)
                        gemini_owner = AccountOwner(
                            kind=OwnerKind.AUTHENTICATED, auth_subject=str(uuid4())
                        )
                        session.add(gemini_owner)
                        await session.flush()
                        gemini_doc = ResearchDocument(
                            owner_id=gemini_owner.id,
                            paper_id=paper.id,
                            filename="gemini-fixture.pdf",
                            byte_size=100,
                            sha256="e" * 64,
                        )
                        session.add(gemini_doc)
                        await session.commit()
                        await check_gemini_binding(
                            session, sessions, gemini_owner, gemini_doc
                        )
                finally:
                    await transaction.rollback()
        finally:
            await engine.dispose()

    asyncio.run(run())
