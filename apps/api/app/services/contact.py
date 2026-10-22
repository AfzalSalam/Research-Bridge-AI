"""Selected-author lookup; public evidence only, no guessed recipient addresses."""

import asyncio
import heapq
import time
from datetime import UTC, datetime, timedelta
from typing import Literal, cast
from urllib.parse import urljoin, urlsplit
from uuid import UUID

import httpx2
from bs4 import BeautifulSoup

from app.clients.institutions import (
    InstitutionRegistry,
    OfficialInstitution,
    RegistryUnavailable,
)
from app.clients.university import CrawlBlocked, UniversityFetcher, approved_url
from app.core.errors import AppError
from app.repositories.contact import ContactIdentity, ContactRepository
from app.schemas.contact import (
    ContactLookupRequest,
    ContactLookupResponse,
    ContactProfile,
    PublicEmail,
)
from app.services.contact_extraction import (
    corroboration,
    document,
    name_matches,
    normalized,
    personal_page,
    public_emails,
)
from app.services.university_scan import UniversityScanService
from app.services.university_sources import SOURCES

ALIASES = {
    "oist": ("okinawa institute", "oist"),
    "kaust": ("king abdullah university", "kaust"),
    "ista": ("institute of science and technology austria", "ista"),
    "iitgn": ("indian institute of technology gandhinagar", "iit gandhinagar"),
    "iitk": ("indian institute of technology kanpur", "iit kanpur"),
    "iisc": ("indian institute of science", "iisc"),
    "epfl": ("ecole polytechnique federale de lausanne", "epfl"),
}
HOSTS = frozenset(host for source in SOURCES.values() for host in source.hosts)


def lookup_sources(identity: ContactIdentity) -> list[str]:
    names = [normalized(name) for name in identity.affiliations]
    return [
        key
        for key, aliases in ALIASES.items()
        if any(
            name == alias or (" " not in alias and alias in name.split())
            for alias in aliases
            for name in names
        )
    ]


async def crawl_contact(
    identity: ContactIdentity,
    profile_url: str | None,
    fetcher: UniversityFetcher,
    *,
    budget: float = 90,
    max_pages: int = 20,
    institutions: list[OfficialInstitution] | None = None,
) -> ContactLookupResponse:
    start = time.monotonic()
    result = ContactLookupResponse(
        author_id=identity.id,
        author_name=identity.name,
        status="not-found",
        checked_at=datetime.now(UTC),
        lookup_url=profile_url,
    )
    keys = lookup_sources(identity)
    institutions = institutions or []
    hosts = HOSTS | frozenset(
        host for institution in institutions for host in institution.hosts
    )
    seeds = (
        [profile_url]
        if profile_url
        else [url for key in keys for url in SOURCES[key].seeds]
    )
    if not profile_url:
        seeds.extend(institution.website for institution in institutions)
    if not seeds:
        result.status = "unsupported"
        result.warnings = [
            "No official website could be verified from this author's institution "
            "metadata. Coverage depends on available registry identifiers."
        ]
        return result
    queue: list[tuple[int, int, str, int]] = []
    queued: set[str] = set()
    counter = 0

    def enqueue(url: str, priority: int, depth: int) -> None:
        nonlocal counter
        try:
            url = approved_url(url, hosts)
        except CrawlBlocked:
            return
        if url not in queued and len(queued) < 120 and depth <= 3:
            heapq.heappush(queue, (priority, counter, url, depth))
            queued.add(url)
            counter += 1

    for seed in seeds:
        enqueue(seed, 0, 0)
    attempted = 0
    while queue and attempted < max_pages:
        remaining = budget - (time.monotonic() - start)
        if remaining <= 0:
            result.warnings.append(
                "Lookup reached its 90-second budget. Try an official profile URL."
            )
            break
        _, _, url, depth = heapq.heappop(queue)
        attempted += 1
        try:
            async with asyncio.timeout(remaining):
                page = await fetcher.fetch(url)
        except (CrawlBlocked, TimeoutError) as error:
            message = str(error) or "Lookup time limit reached."
            result.warnings.append(f"{urlsplit(url).hostname}: {message}")
            continue
        result.pages_checked += 1
        soup = document(page.html)
        personal = personal_page(identity, soup)
        evidence = corroboration(identity, soup) if personal else []
        emails = public_emails(soup, identity) if personal else []
        if personal:
            reason = (
                "Name matches, but identity or individual email "
                "attribution needs review."
            )
            if not emails:
                reason = "Matching name; no unambiguous public address extracted."
            result.profiles.append(ContactProfile(source_url=page.url, reason=reason))
        if (
            personal
            and evidence
            and emails
            and len({item.email.split("@")[0] for item in emails}) == 1
        ):
            for email in emails[:3]:
                result.emails.append(
                    PublicEmail(
                        email=email.email,
                        source_url=page.url,
                        identity_evidence=[
                            "Name matches the official page title or heading",
                            *evidence,
                        ],
                        evidence_urls=[page.url],
                        extraction=cast(
                            Literal["mailto", "text", "obfuscated"], email.extraction
                        ),
                        checked_at=datetime.now(UTC),
                    )
                )
            result.profiles[-1].reason = "Name and independent identity evidence match."
            result.status = "found"
            break
        for link in BeautifulSoup(page.html, "html.parser").select("a[href]"):
            try:
                target = urljoin(page.url, str(link.get("href", "")))
            except ValueError:
                continue
            label = link.get_text(" ", strip=True)
            context = link.parent.get_text(" ", strip=True) if link.parent else label
            named = name_matches(identity.name, label) or (
                len(context) < 300 and name_matches(identity.name, context)
            )
            directory = any(
                word in normalized(label).split()
                for word in ("faculty", "people", "profiles", "members", "team")
            )
            # Once a personal page is found, its contact/about/publication pages may
            # provide both identity and email evidence. Never transfer another
            # page's identifier to an uncorroborated recipient.
            related = personal and any(
                word in normalized(label).split()
                for word in ("contact", "about", "publications", "biography")
            )
            if named or directory or related:
                enqueue(target, -10 if named else -5 if related else 1, depth + 1)
    if result.status != "found":
        result.status = (
            "needs-review"
            if result.profiles
            else "blocked"
            if result.pages_checked == 0
            else "not-found"
        )
    if queue and attempted >= max_pages:
        result.warnings.append(
            "Reached the 20-page limit. Supply a specific official profile "
            "to narrow the lookup."
        )
    result.profiles = list(
        {profile.source_url: profile for profile in result.profiles}.values()
    )[:8]
    result.warnings = list(dict.fromkeys(result.warnings))[:10]
    result.elapsed_seconds = int(time.monotonic() - start)
    return result


class ContactService:
    def __init__(
        self,
        repository: ContactRepository,
        scanner: UniversityScanService,
        registry: InstitutionRegistry | None = None,
    ) -> None:
        self.repository = repository
        self.scanner = scanner
        self.registry = registry or InstitutionRegistry()

    async def lookup(
        self, author_id: UUID, owner_id: UUID, body: ContactLookupRequest
    ) -> ContactLookupResponse:
        identity = await self.repository.identity(author_id)
        if identity is None:
            raise AppError(
                code="author_not_found",
                message="Search for and select a researcher first.",
                status_code=404,
            )
        url = body.profile_url
        cached = await self.repository.cached(author_id)
        if cached and not body.refresh and cached.lookup_url == url:
            age = datetime.now(UTC) - cached.checked_at.replace(tzinfo=UTC)
            ttl = timedelta(days=7) if cached.status == "found" else timedelta(hours=1)
            if age < ttl:
                return cached.model_copy(update={"cache_hit": True})
        token = self.scanner.reserve(str(owner_id))
        started = time.monotonic()
        institutions: list[OfficialInstitution] = []
        warnings: list[str] = []
        try:
            try:
                async with asyncio.timeout(20):
                    for identifier in identity.ror_ids[:6]:
                        try:
                            institution = await self.registry.resolve(identifier)
                            if institution:
                                institutions.append(institution)
                        except RegistryUnavailable as error:
                            warnings.append(str(error))
                            break
            except TimeoutError:
                warnings.append("Institution verification reached its time budget.")
            hosts = HOSTS | frozenset(h for item in institutions for h in item.hosts)
            if url:
                try:
                    url = approved_url(url, hosts)
                except CrawlBlocked as error:
                    raise AppError(
                        code="profile_url_not_supported",
                        message=(
                            "This URL is not on an official domain verified "
                            "for the author's institutions."
                        ),
                        status_code=422,
                    ) from error
            async with httpx2.AsyncClient(
                timeout=httpx2.Timeout(8, connect=5),
                follow_redirects=False,
                trust_env=False,
                limits=httpx2.Limits(max_connections=2, max_keepalive_connections=0),
            ) as client:
                fetcher = UniversityFetcher(client, hosts, self.scanner.pacer)
                result = await crawl_contact(
                    identity,
                    url,
                    fetcher,
                    budget=max(1, 90 - (time.monotonic() - started)),
                    institutions=institutions,
                )
            result.warnings = list(dict.fromkeys([*warnings, *result.warnings]))
            result.institution_sources = [item.ror_id for item in institutions]
            result.elapsed_seconds = int(time.monotonic() - started)
            await self.repository.save(result)
            return result
        finally:
            self.scanner.release(str(owner_id), token)
