"""Guarded execution foundation. No route enables this service yet."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.documents.answer_usage import AnswerRequest, reserve_answer
from app.documents.answers import AnswerProvider, AnswerResult, answer, load_evidence
from app.documents.history import ensure_unused, save_history
from app.documents.repository import DocumentRepository
from app.documents.retrieval import PassageQuery, retrieve


class PaperAnswers:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        provider: AnswerProvider | None,
        *,
        enabled: bool = False,
        daily_call_limit: int = 30,
        require_postgres: bool = True,
    ) -> None:
        if daily_call_limit < 3:
            raise ValueError("Daily allowance must cover one answer")
        self.sessions = sessions
        self.provider = provider
        self.enabled = enabled
        self.daily_call_limit = daily_call_limit
        self.require_postgres = require_postgres

    async def ask(
        self, owner: UUID, document: UUID, request: AnswerRequest
    ) -> AnswerResult:
        async with self.sessions() as session:
            await DocumentRepository(session).pages(owner, document)
            if (
                not self.enabled
                or self.provider is None
                or (
                    self.require_postgres
                    and session.get_bind().dialect.name != "postgresql"
                )
            ):
                raise AppError(
                    code="paper_answers_unavailable",
                    message="Paper answers are not enabled yet.",
                    status_code=503,
                )
            await ensure_unused(session, owner, request)
            # Retrieval is server-side; callers cannot supply their own evidence.
            retrieved = await retrieve(
                session, owner, document, PassageQuery(query=request.question, limit=5)
            )
            evidence = await load_evidence(session, owner, document, retrieved.passages)
            if not evidence:
                result = AnswerResult(
                    status="insufficient_evidence", reason="no_passages"
                )
                await save_history(session, owner, document, request, result)
                await session.commit()
                return result
            await reserve_answer(
                session,
                owner,
                document,
                request,
                daily_call_limit=self.daily_call_limit,
            )
            await session.commit()
        # Session and owner lock are closed before any external call.
        result = await answer(request.question, evidence, self.provider)
        async with self.sessions() as session:
            try:
                current = await load_evidence(
                    session, owner, document, retrieved.passages
                )
            except ValueError:
                raise AppError(
                    code="paper_source_changed",
                    message="Paper text changed. Refresh before asking again.",
                    status_code=409,
                ) from None
            if current != evidence:
                raise AppError(
                    code="paper_source_changed",
                    message="Paper text changed. Refresh before asking again.",
                    status_code=409,
                )
            await save_history(session, owner, document, request, result)
            await session.commit()
        return result
