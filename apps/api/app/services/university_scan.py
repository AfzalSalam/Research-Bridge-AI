"""Request-scoped, cancellable scans. Partial results are never padded."""

from __future__ import annotations

import asyncio
import heapq
import re
import time
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime

import httpx2

from app.clients.university import CrawlBlocked, HostPacer, UniversityFetcher
from app.core.errors import AppError
from app.schemas.university import (
    UniversityScanRequest,
    UniversityScanSnapshot,
    UniversitySourceSummary,
)
from app.services.university_extraction import (
    crawl_links,
    document,
    extract_papers,
    extract_program,
    terms,
)
from app.services.university_sources import SOURCES, UniversitySource, selected_sources


class UniversityScanService:
    def __init__(self) -> None:
        self.active_owners: dict[str, object] = {}
        self.pacer = HostPacer()

    def reserve(self, owner: str) -> object:
        if owner in self.active_owners or len(self.active_owners) >= 2:
            raise AppError(
                code="scan_busy",
                message="A university scan is already "
                "running. Wait for it to finish or cancel it.",
                status_code=429,
            )
        token = object()
        self.active_owners[owner] = token
        return token

    def release(self, owner: str, token: object) -> None:
        if self.active_owners.get(owner) is token:
            self.active_owners.pop(owner, None)

    async def scan(
        self,
        request: UniversityScanRequest,
        *,
        extra_sources: dict[str, UniversitySource] | None = None,
        initial_elapsed: float = 0,
        warnings: list[str] | None = None,
    ) -> AsyncIterator[UniversityScanSnapshot]:
        keys = selected_sources(request.region, request.universities)
        sources = {key: SOURCES[key] for key in keys}
        sources = {**(extra_sources or {}), **sources}
        hosts = frozenset(h for source in sources.values() for h in source.hosts)
        async with httpx2.AsyncClient(
            timeout=httpx2.Timeout(8, connect=5),
            follow_redirects=False,
            trust_env=False,
            limits=httpx2.Limits(max_connections=2, max_keepalive_connections=0),
        ) as client:
            fetcher = UniversityFetcher(client, hosts, self.pacer)
            async for snapshot in scan_pages(
                request,
                fetcher,
                sources=sources,
                initial_elapsed=initial_elapsed,
                warnings=warnings,
            ):
                yield snapshot


async def scan_pages(
    request: UniversityScanRequest,
    fetcher: UniversityFetcher,
    *,
    budget: float = 120,
    max_pages: int = 40,
    sources: dict[str, UniversitySource] | None = None,
    initial_elapsed: float = 0,
    warnings: list[str] | None = None,
) -> AsyncIterator[UniversityScanSnapshot]:
    start = time.monotonic() - initial_elapsed
    sources = (
        sources
        if sources is not None
        else {
            key: SOURCES[key]
            for key in selected_sources(request.region, request.universities)
        }
    )
    snapshot = UniversityScanSnapshot(
        state="scanning",
        query=request.query,
        target=request.target,
        sources=[
            UniversitySourceSummary(
                name=source.name,
                website=source.program_url,
                registry_url=key if key.startswith("https://ror.org/") else None,
            )
            for key, source in sources.items()
        ],
        budget_seconds=int(budget),
        elapsed_seconds=int(initial_elapsed),
        warnings=warnings or [],
    )
    yield snapshot.model_copy(deep=True)
    query_terms = terms(request.query)
    if not query_terms:
        snapshot.state = "empty"
        snapshot.stop_reason = "no_search_terms"
        snapshot.warnings = [
            "Use a specific research topic rather than generic internship keywords."
        ]
        yield snapshot
        return
    queue: list[tuple[int, int, str, int, str]] = []
    counter = 0
    queued: set[str] = set()
    keys = list(sources)
    for key in keys:
        source = sources[key]
        for index, url in enumerate((source.program_url, *source.seeds)):
            heapq.heappush(queue, (-1000 + index, counter, url, 0, key))
            queued.add(url)
            counter += 1
    seen_papers: set[str] = set()
    pages_by_source: dict[str, int] = {}
    while queue and snapshot.pages_attempted < max_pages:
        remaining = budget - (time.monotonic() - start)
        if remaining <= 0:
            snapshot.stop_reason = "time_limit"
            break
        _, _, url, depth, key = heapq.heappop(queue)
        source = sources[key]
        # A single large university must not consume the whole scan.
        if pages_by_source.get(key, 0) >= max(12, max_pages // max(1, len(keys))):
            continue
        pages_by_source[key] = pages_by_source.get(key, 0) + 1
        snapshot.current_university = source.name
        snapshot.pages_attempted += 1
        try:
            async with asyncio.timeout(min(remaining, 20)):
                page = await fetcher.fetch(url)
            snapshot.pages_read += 1
            now = datetime.now(UTC)
            soup = document(page.html)
            if url == source.program_url and source.program_verified_seed:
                snapshot.programs.append(extract_program(soup, source, page.url, now))
            elif not source.program_verified_seed:
                heading = " ".join(
                    tag.get_text(" ", strip=True) for tag in soup.select("title, h1")
                )
                if re.search(
                    r"research.{0,35}internship|summer.{0,25}research.{0,25}(?:program|fellowship|internship)",
                    heading,
                    re.I,
                ):
                    program = extract_program(
                        soup, replace(source, program_name=heading[:160]), page.url, now
                    )
                    if not any(
                        item.source_url == program.source_url
                        for item in snapshot.programs
                    ):
                        snapshot.programs.append(program)
            for paper in extract_papers(soup, page.url, source.name, query_terms, now):
                if paper.id not in seen_papers:
                    seen_papers.add(paper.id)
                    snapshot.papers.append(paper)
                    if len(snapshot.papers) == request.target:
                        break
            snapshot.papers.sort(key=lambda p: (-len(p.matched_terms), p.citation))
            if depth < 3:
                for priority, link in crawl_links(soup, page.url, source, query_terms):
                    if link in queued:
                        continue
                    candidate = (-priority, counter, link, depth + 1, key)
                    if len(queue) >= 240:
                        # A large directory must not crowd out a publication
                        # link discovered later on a relevant faculty page.
                        worst = max(queue)
                        if candidate >= worst:
                            continue
                        queue.remove(worst)
                        queued.discard(worst[2])
                        heapq.heapify(queue)
                    queued.add(link)
                    heapq.heappush(queue, candidate)
                    counter += 1
        except (CrawlBlocked, TimeoutError) as error:
            reason = (
                str(error)
                if isinstance(error, CrawlBlocked)
                else "Page time limit reached."
            )
            warning = f"{source.name}: {reason}"
            if warning not in snapshot.warnings:
                snapshot.warnings.append(warning)
        snapshot.elapsed_seconds = int(time.monotonic() - start)
        yield snapshot.model_copy(deep=True)
        if len(snapshot.papers) >= request.target:
            snapshot.stop_reason = "target_reached"
            break
    snapshot.current_university = None
    snapshot.elapsed_seconds = int(time.monotonic() - start)
    snapshot.stop_reason = snapshot.stop_reason or (
        "page_limit"
        if snapshot.pages_attempted >= max_pages
        else "reviewed_links_exhausted"
    )
    snapshot.state = (
        "complete"
        if len(snapshot.papers) == request.target
        else "partial"
        if snapshot.papers or snapshot.programs
        else "empty"
    )
    yield snapshot
