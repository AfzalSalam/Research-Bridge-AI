"""Indexing worker service; not automatically invoked by document uploads."""

import argparse
import asyncio
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import AppError
from app.db.models import IndexJob
from app.db.session import create_database
from app.documents.embeddings import (
    EMBEDDING_DIMENSIONS,
    EmbeddingBatch,
    EmbeddingError,
)
from app.documents.indexing import IndexRepository
from app.documents.providers import OPENAI, EmbeddingPolicy, create_embedder, policy
from app.documents.vectors import valid_batch


class Embedder(Protocol):
    async def embed(self, inputs: list[str]) -> EmbeddingBatch: ...


class IndexWorker:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        provider: Embedder,
        *,
        daily_limit: int,
        embedding_policy: EmbeddingPolicy = OPENAI,
    ) -> None:
        self.sessions, self.provider, self.daily_limit = sessions, provider, daily_limit
        self.policy = embedding_policy

    async def process_one(self) -> bool:
        async with self.sessions() as session:
            lease = await IndexRepository(session, self.policy).claim(self.daily_limit)
            await session.commit()
        if lease is None:
            return False
        vectors: list[tuple[float, ...]] = []
        tokens = 0
        try:
            for offset in range(0, len(lease.chunks), self.policy.batch_size):
                async with self.sessions() as session:
                    active = await IndexRepository(session, self.policy).renew(lease)
                    await session.commit()
                if not active:
                    return True
                batch = await self.provider.embed(
                    [
                        c.text
                        for c in lease.chunks[offset : offset + self.policy.batch_size]
                    ]
                )
                if batch.model != self.policy.model or not valid_batch(
                    batch, len(lease.chunks[offset : offset + self.policy.batch_size])
                ):
                    raise EmbeddingError("invalid_embedding_response")
                vectors.extend(batch.vectors)
                tokens += batch.prompt_tokens
            async with self.sessions() as session:
                await IndexRepository(session, self.policy).finish(
                    lease,
                    EmbeddingBatch(
                        self.policy.model, EMBEDDING_DIMENSIONS, tuple(vectors), tokens
                    ),
                )
                await session.commit()
        except (EmbeddingError, AppError) as error:
            # Unknown provider outcomes keep their conservative reservation.
            async with self.sessions() as session:
                await IndexRepository(session, self.policy).finish(
                    lease,
                    None,
                    error=error.code,
                    retry_after=error.retry_after
                    if isinstance(error, EmbeddingError)
                    else 0,
                )
                await session.commit()
        return True


async def run(*, once: bool, status: bool) -> None:
    settings = Settings()
    database = create_database(settings)
    try:
        if status:
            async with database.session_factory() as session:
                rows = await session.execute(
                    select(IndexJob.status, func.count()).group_by(IndexJob.status)
                )
                print({state: count for state, count in rows})
            return
        if not settings.document_indexing_enabled:
            raise SystemExit(
                "Semantic indexing is disabled. "
                "Set DOCUMENT_INDEXING_ENABLED only after setup."
            )
        if database.engine.dialect.name != "postgresql":
            raise SystemExit("Semantic indexing requires PostgreSQL.")
        try:
            provider = create_embedder(settings)
        except EmbeddingError:
            raise SystemExit(
                "Configure the server-side embedding provider key before indexing."
            ) from None
        try:
            worker = IndexWorker(
                database.session_factory,
                provider,
                daily_limit=settings.document_embedding_daily_limit,
                embedding_policy=policy(settings),
            )
            while True:
                worked = await worker.process_one()
                if once:
                    return
                if not worked:
                    await asyncio.sleep(5)
        finally:
            await provider.aclose()
    finally:
        await database.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process consented paper embedding jobs."
    )
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(once=args.once, status=args.status))
