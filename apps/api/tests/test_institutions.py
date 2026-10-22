from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.clients.institutions import (
    InstitutionRegistry,
    RegistryRecord,
    official_institution,
)
from app.clients.university import FetchedPage
from app.schemas.university import UniversityScanRequest
from app.services.institution_discovery import GlobalUniversityDiscovery
from app.services.university_scan import scan_pages


@pytest.fixture
def anyio_backend():
    return "asyncio"


def record(**changes):
    data = dict(
        id="https://ror.org/042nb2s44",
        status="active",
        names=[dict(value="Test University", types=["ror_display"])],
        links=[dict(type="website", value="http://www.mit.edu/")],
        domains=["mit.edu"],
        types=["education"],
    )
    data.update(changes)
    return RegistryRecord.model_validate(data)


def test_registry_domain_requires_matching_active_record():
    institution = official_institution(record(), "042nb2s44")
    assert institution.website == "https://www.mit.edu/"
    assert institution.hosts == frozenset({"mit.edu"})
    assert official_institution(record(status="inactive"), "042nb2s44") is None
    assert official_institution(record(), "000000000") is None
    for url in [
        "https://127.0.0.1/",
        "https://ac.in/",
        "https://user:pass@mit.edu/",
        "https://mit.edu:8080/",
    ]:
        assert (
            official_institution(
                record(links=[dict(type="website", value=url)]), "042nb2s44"
            )
            is None
        )


@pytest.mark.anyio
async def test_registry_rejects_arbitrary_identifier_without_network():
    assert await InstitutionRegistry().resolve("https://evil.com/042nb2s44") is None


@pytest.mark.anyio
async def test_global_sources_region_and_no_homepage_opening():
    official = official_institution(record(), "042nb2s44")
    registry = SimpleNamespace(resolve=AsyncMock(return_value=official))
    author = SimpleNamespace(
        institutions=[SimpleNamespace(ror_id=official.ror_id, country_code="US")]
    )
    papers = SimpleNamespace(
        search=AsyncMock(
            return_value=SimpleNamespace(
                papers=[SimpleNamespace(authors=[author])], warnings=[]
            )
        )
    )
    discovery = GlobalUniversityDiscovery(papers, registry)
    sources, warnings = await discovery.sources(
        UniversityScanRequest(query="machine learning")
    )
    assert list(sources) == [official.ror_id]
    assert not sources[official.ror_id].program_verified_seed
    assert "partial coverage" in warnings[-1]
    india, _ = await discovery.sources(
        UniversityScanRequest(query="machine learning", region="india")
    )
    assert india == {}
    fetcher = SimpleNamespace(
        fetch=AsyncMock(
            return_value=FetchedPage(
                official.website,
                "<h1>Test University</h1><p>Machine learning research</p>",
            )
        )
    )
    snapshots = [
        s
        async for s in scan_pages(
            UniversityScanRequest(query="machine learning"), fetcher, sources=sources
        )
    ]
    assert snapshots[-1].programs == []
    assert snapshots[-1].sources[0].registry_url == official.ror_id
    fetcher.fetch.return_value = FetchedPage(
        official.website,
        "<h1>Summer research internship</h1><p>Machine learning research</p>",
    )
    snapshots = [
        s
        async for s in scan_pages(
            UniversityScanRequest(query="machine learning"), fetcher, sources=sources
        )
    ]
    assert len(snapshots[-1].programs) == 1
    assert snapshots[-1].programs[0].work_mode == "not-specified"


@pytest.mark.anyio
async def test_registry_cache_and_rate_limit(monkeypatch):
    import httpx

    from app.clients.institutions import RegistryUnavailable

    original = httpx.AsyncClient
    calls = []

    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(200, json=record().model_dump())

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs),
    )
    registry = InstitutionRegistry()
    assert await registry.resolve("042nb2s44") is not None
    assert await registry.resolve("https://ror.org/042nb2s44") is not None
    assert calls == ["https://api.ror.org/v2/organizations/042nb2s44"]
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(
            transport=httpx.MockTransport(lambda request: httpx.Response(429)), **kwargs
        ),
    )
    with pytest.raises(RegistryUnavailable, match="rate limited"):
        await InstitutionRegistry().resolve("042nb2s44")


@pytest.mark.anyio
async def test_contact_crawls_verified_institution_outside_original_seven():
    from dataclasses import replace

    from app.services.contact import crawl_contact
    from tests.test_contact import HTML, IDENTITY

    official = official_institution(record(), "042nb2s44")
    identity = replace(
        IDENTITY, affiliations=("Test University",), ror_ids=(official.ror_id,)
    )
    html = HTML.replace("iitk.ac.in", "mit.edu")
    fetcher = SimpleNamespace(
        fetch=AsyncMock(return_value=FetchedPage(official.website, html))
    )
    result = await crawl_contact(identity, None, fetcher, institutions=[official])
    assert result.status == "found"
    assert result.emails[0].email == "mira.sen@mit.edu"
    assert result.emails[0].source_url == official.website
