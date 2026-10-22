import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from app.core.errors import AppError
from app.db.models import (
    AnswerReservation,
    DocumentPage,
    ReadingAnswer,
    ResearchDocument,
)
from app.documents.answer_service import PaperAnswers
from app.documents.answers import AnswerProviderError
from app.documents.history import read_history
from tests.test_answer_usage import request
from tests.test_document_repository import exercise
from tests.test_document_vectors import seed


@pytest.mark.parametrize(
    "mode", ["answer", "abstain", "failure", "cancel", "delete", "change"]
)
def test_committed_reservation_and_post_call_access(migrated_database_url, mode):
    async def scenario(session, sessions, owner, doc):
        await seed(session, doc)
        provider = AsyncMock()

        async def generate(*args):
            async with sessions() as observer:
                assert (
                    await observer.scalar(
                        select(func.count()).select_from(AnswerReservation)
                    )
                    == 1
                )
                if mode == "delete":
                    await observer.execute(
                        delete(ResearchDocument).where(ResearchDocument.id == doc.id)
                    )
                    await observer.commit()
            if mode == "failure":
                raise AnswerProviderError("safe_failure")
            if mode == "cancel":
                raise asyncio.CancelledError()
            if mode == "change":
                async with sessions() as writer:
                    page = await writer.scalar(
                        select(DocumentPage).where(DocumentPage.document_id == doc.id)
                    )
                    page.text = "Changed source text."
                    await writer.commit()
            if mode == "answer":
                return (
                    '{"status":"answer","claims":[{"text":"Graph attention method.",'
                    '"citations":[{"passage_id":"p0",'
                    '"quote":"Graph attention method."}]}]}'
                )
            return '{"status":"insufficient_evidence","claims":[]}'

        provider.generate.side_effect = generate
        provider.review.return_value = (
            '{"addresses_question":true,"claims":[{"index":0,"verdict":"supported"}]}'
        )
        service = PaperAnswers(
            sessions, provider, enabled=True, require_postgres=False, daily_call_limit=3
        )
        req = request(question="Graph attention")
        if mode == "cancel":
            with pytest.raises(asyncio.CancelledError):
                await service.ask(owner.id, doc.id, req)
        elif mode in ("delete", "change"):
            with pytest.raises(AppError) as caught:
                await service.ask(owner.id, doc.id, req)
            assert caught.value.status_code == (404 if mode == "delete" else 409)
        else:
            result = await service.ask(owner.id, doc.id, req)
            assert result.reason == (
                "provider_unavailable"
                if mode == "failure"
                else "reviewed"
                if mode == "answer"
                else "source_insufficient"
            )
            with pytest.raises(AppError) as duplicate:
                await service.ask(owner.id, doc.id, req)
            assert duplicate.value.code == "answer_request_used"
        async with sessions() as observer:
            assert (
                await observer.scalar(
                    select(func.count()).select_from(AnswerReservation)
                )
                == 1
            )
        async with sessions() as observer:
            count = await observer.scalar(
                select(func.count()).select_from(ReadingAnswer)
            )
            assert count == (0 if mode in ("cancel", "delete", "change") else 1)
            if count:
                entries = await read_history(observer, owner.id, doc.id)
                assert entries[0].question == "Graph attention"
                assert entries[0].result == result
                with pytest.raises(AppError) as denied:
                    await read_history(observer, uuid4(), doc.id)
                assert denied.value.status_code == 404
                await observer.execute(
                    delete(ResearchDocument).where(ResearchDocument.id == doc.id)
                )
                await observer.commit()
                assert (
                    await observer.scalar(
                        select(func.count()).select_from(ReadingAnswer)
                    )
                    == 0
                )
        provider.generate.assert_awaited_once()

    asyncio.run(exercise(migrated_database_url, scenario))


def test_disabled_wrong_owner_empty_and_postgres_guards(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        await seed(session, doc)
        provider = AsyncMock()
        req = request(question="Graph")
        for service in [
            PaperAnswers(sessions, provider),
            PaperAnswers(sessions, provider, enabled=True),
        ]:
            with pytest.raises(AppError) as unavailable:
                await service.ask(owner.id, doc.id, req)
            assert unavailable.value.status_code == 503
        service = PaperAnswers(sessions, provider, enabled=True, require_postgres=False)
        with pytest.raises(AppError) as denied:
            await service.ask(uuid4(), doc.id, req)
        assert denied.value.status_code == 404
        result = await service.ask(owner.id, doc.id, request(question="Unfindableword"))
        assert result.reason == "no_passages"
        provider.generate.assert_not_awaited()
        assert (
            await session.scalar(select(func.count()).select_from(AnswerReservation))
            == 0
        )

    asyncio.run(exercise(migrated_database_url, scenario))
