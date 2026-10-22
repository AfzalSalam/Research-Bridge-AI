import asyncio
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, func, select

from app.core.errors import AppError
from app.db.models import AccountOwner, AnswerReservation, ResearchDocument
from app.documents.answer_usage import ANSWER_DISCLOSURE, AnswerRequest, reserve_answer
from tests.test_document_repository import exercise
from tests.test_document_vectors import seed


def request(**changes):
    return AnswerRequest(
        **dict(
            {
                "request_id": uuid4(),
                "question": "Which method?",
                "accepted": True,
                "disclosure_version": ANSWER_DISCLOSURE,
            },
            **changes,
        )
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"accepted": False},
        {"accepted": 1},
        {"accepted": "true"},
        {"disclosure_version": "old"},
        {"question": " "},
    ],
)
def test_consent_and_question_validation(changes):
    with pytest.raises(ValidationError):
        request(**changes)


def test_usage_owner_duplicate_quota_and_deletion(migrated_database_url):
    async def scenario(session, sessions, owner, doc):
        await seed(session, doc)
        with pytest.raises(AppError) as denied:
            await reserve_answer(
                session, uuid4(), doc.id, request(), daily_call_limit=3
            )
        assert denied.value.status_code == 404
        req = request()
        token = await reserve_answer(session, owner.id, doc.id, req, daily_call_limit=3)
        await session.commit()
        async with sessions() as observer:
            row = await observer.get(AnswerReservation, token)
            assert row is not None and row.reserved_calls == 3
            assert row.disclosure_version == ANSWER_DISCLOSURE
            assert not hasattr(row, "question")
        with pytest.raises(AppError) as repeated:
            await reserve_answer(session, owner.id, doc.id, req, daily_call_limit=3)
        assert repeated.value.code == "answer_request_used"
        with pytest.raises(AppError) as quota:
            await reserve_answer(
                session, owner.id, doc.id, request(), daily_call_limit=3
            )
        assert quota.value.status_code == 429
        await session.execute(
            delete(ResearchDocument).where(ResearchDocument.id == doc.id)
        )
        await session.commit()
        assert (
            await session.scalar(select(func.count()).select_from(AnswerReservation))
            == 1
        )
        await session.execute(delete(AccountOwner).where(AccountOwner.id == owner.id))
        await session.commit()
        assert (
            await session.scalar(select(func.count()).select_from(AnswerReservation))
            == 0
        )

    asyncio.run(exercise(migrated_database_url, scenario))
