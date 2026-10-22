"""Evidence, crawl boundaries, cancellation slots, and streaming contract."""

import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx2
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.clients.university import (
    CrawlBlocked,
    FetchedPage,
    UniversityFetcher,
    approved_url,
)
from app.core.config import Settings
from app.core.errors import AppError
from app.dependencies.authentication import (
    AuthenticatedPrincipal,
    get_current_principal,
)
from app.main import create_app
from app.schemas.university import UniversityScanRequest, UniversityScanSnapshot
from app.services.university_extraction import (
    document,
    extract_papers,
    extract_program,
    work_mode,
)
from app.services.university_scan import UniversityScanService, scan_pages
from app.services.university_sources import SOURCES


@pytest.fixture
def anyio_backend():
    return "asyncio"


NOW = datetime(2026, 10, 9, tzinfo=UTC)
HOSTS = frozenset({"oist.jp"})


def citation(index: int) -> str:
    return f'<li>Machine learning for robotics {index} <a href="https://doi.org/10.1234/p{index}">DOI</a></li>'


@pytest.mark.parametrize(
    "url",
    [
        "http://oist.jp/",
        "https://oist.jp.evil.com/",
        "https://evil.com/",
        "https://oist.jp@127.0.0.1/",
        "https://oist.jp:8080/",
        "https://oist.jp/search?q=x",
        "https://oist.jp/\\evil",
        "https://oist.jp/\nfoo",
    ],
)
def test_url_boundary(url):
    with pytest.raises(CrawlBlocked):
        approved_url(url, HOSTS)


def test_request_rejects_unapproved_source_and_target():
    for payload in (
        {"target": 99},
        {"universities": ["other"]},
        {"universities": ["oist", "oist"]},
    ):
        with pytest.raises(ValidationError):
            UniversityScanRequest(query="machine learning", **payload)


def test_publication_evidence_and_normalized_duplicates():
    html = (
        citation(1)
        + citation(1)
        + '<li>Unrelated biology <a href="https://doi.org/10.1234/bio">DOI</a></li>'
    )
    html += '<a href="https://[bad">Malformed</a><p>Professor accepting interns</p>'
    papers = extract_papers(
        document(html), "https://oist.jp/lab", "OIST", ["machine", "learning"], NOW
    )
    assert len(papers) == 2
    assert papers[0].id == papers[1].id
    assert papers[0].title is None
    assert papers[0].source_url == "https://oist.jp/lab"
    assert papers[0].checked_at == NOW


def test_arxiv_versions_share_identity():
    html = '<p>Machine learning for robotics <a href="https://arxiv.org/abs/2301.12345v1">Paper</a></p>'
    html += '<p>Machine learning for robotics revised <a href="https://arxiv.org/abs/2301.12345v2">Paper</a></p>'
    papers = extract_papers(
        document(html), "https://oist.jp/lab", "OIST", ["machine"], NOW
    )
    assert papers[0].id == papers[1].id


@pytest.mark.parametrize(
    ("text", "mode"),
    [
        ("Remote internships are available.", "remote"),
        ("Interns will work remotely.", "remote"),
        ("The internship will be conducted in offline mode.", "on-site"),
        ("A hybrid internship is offered.", "hybrid"),
        ("Remote internships are not available.", "not-specified"),
        ("Internship applicants attend an in-person interview.", "not-specified"),
        ("Interns receive housing on campus.", "not-specified"),
    ],
)
def test_mode_requires_explicit_work_evidence(text, mode):
    assert work_mode([text])[0] == mode
    assert (
        work_mode(["Remote internships available.", "On-site internships available."])[
            0
        ]
        == "not-specified"
    )


def test_program_dates_do_not_use_start_dates_or_invent_mode():
    html = (
        "<table><tr><th>Deadline</th><th>Start</th></tr>"
        "<tr><td>March 5, 2026</td><td>January 1, 2027</td></tr></table>"
    )
    result = extract_program(
        document(html), SOURCES["iitgn"], SOURCES["iitgn"].program_url, NOW
    )
    assert result.status == "closed"
    assert result.deadline == "2026-03-05"
    assert result.work_mode == "not-specified"
    assert result.eligibility_evidence is None
    result = extract_program(
        document("<p>Applications are accepted on a continuous basis.</p>"),
        SOURCES["ista"],
        SOURCES["ista"].program_url,
        NOW,
    )
    assert result.status == "rolling"


class NoWait:
    async def wait(self, host, delay):
        pass


@pytest.mark.anyio
async def test_robots_denial_and_html_policy_fail_closed(monkeypatch):
    async def public(host):
        return "93.184.216.34"

    monkeypatch.setattr("app.clients.university.public_address", public)
    for body, content_type in [
        ("User-agent: *\nDisallow: /", "text/plain"),
        ("<html>Login</html>", "text/html"),
    ]:
        requested = []

        def handler(request, requested=requested, body=body, content_type=content_type):
            requested.append(request)
            return httpx2.Response(
                200, text=body, headers={"content-type": content_type}
            )

        async with httpx2.AsyncClient(
            transport=httpx2.MockTransport(handler)
        ) as client:
            fetcher = UniversityFetcher(client, HOSTS, NoWait())
            with pytest.raises(CrawlBlocked):
                await fetcher.fetch("https://oist.jp/lab")
        assert len(requested) == 1
        assert requested[0].url.host == "93.184.216.34"
        assert requested[0].headers["host"] == "oist.jp"
        assert requested[0].extensions["sni_hostname"] == "oist.jp"


@pytest.mark.anyio
async def test_redirect_cannot_leave_allowlist(monkeypatch):
    async def public(host):
        return "93.184.216.34"

    monkeypatch.setattr("app.clients.university.public_address", public)
    requested = []

    def handler(request):
        requested.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx2.Response(404)
        return httpx2.Response(302, headers={"location": "https://127.0.0.1/private"})

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
        with pytest.raises(CrawlBlocked):
            await UniversityFetcher(client, HOSTS, NoWait()).fetch(
                "https://oist.jp/lab"
            )
    assert len(requested) == 2


@pytest.mark.anyio
async def test_private_dns_answer_is_rejected(monkeypatch):
    from app.clients.university import public_address

    async def resolve(*args, **kwargs):
        return [(2, 1, 6, "", ("127.0.0.1", 443))]

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", resolve)
    with pytest.raises(CrawlBlocked, match="Non-public"):
        await public_address("oist.jp")


class Pages:
    def __init__(self, html):
        self.html = html

    async def fetch(self, url):
        return FetchedPage(url, self.html)


@pytest.mark.anyio
async def test_target_cap_dedup_and_partial_results():
    request = UniversityScanRequest(
        query="machine learning", target=10, universities=["oist"]
    )
    snapshots = [s async for s in scan_pages(request, Pages(citation(1) * 2))]
    assert snapshots[-1].state == "partial"
    assert len(snapshots[-1].papers) == 1
    snapshots = [
        s
        async for s in scan_pages(
            request, Pages("".join(citation(i) for i in range(20)))
        )
    ]
    assert snapshots[-1].state == "complete"
    assert len(snapshots[-1].papers) == 10
    assert snapshots[-1].stop_reason == "target_reached"
    snapshots = [s async for s in scan_pages(request, Pages(""), budget=0)]
    assert snapshots[-1].stop_reason == "time_limit"
    assert snapshots[-1].pages_attempted == 0


def test_slots_cannot_be_released_by_stale_cleanup():
    service = UniversityScanService()
    old = service.reserve("one")
    with pytest.raises(AppError):
        service.reserve("one")
    service.release("one", old)
    new = service.reserve("one")
    service.release("one", old)
    assert service.active_owners["one"] is new
    service.reserve("two")
    with pytest.raises(AppError):
        service.reserve("three")


def test_authenticated_stream_and_cleanup():
    app = create_app(Settings(app_environment="test"))
    principal = AuthenticatedPrincipal(owner_id=uuid4(), subject="test")
    app.dependency_overrides[get_current_principal] = lambda: principal
    scanner = app.state.university_scanner

    async def scan(request, **kwargs):
        yield UniversityScanSnapshot(
            state="partial", query=request.query, target=request.target
        )

    scanner.scan = scan
    with TestClient(app, raise_server_exceptions=True) as client:
        response = client.post(
            "/api/v1/discovery/universities/scan",
            json={"query": "robotics", "target": 20, "universities": ["ista"]},
        )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    payload = json.loads(response.text.removeprefix("data: "))
    assert payload["state"] == "partial"
    assert payload["target"] == 20
    assert not scanner.active_owners


def test_anonymous_scan_is_denied(migrated_database_url):
    app = create_app(
        Settings(app_environment="test", database_url=migrated_database_url)
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/discovery/universities/scan", json={"query": "machine learning"}
        )
    assert response.status_code == 401
    assert not app.state.university_scanner.active_owners


@pytest.mark.anyio
async def test_size_and_rate_limits(monkeypatch):
    async def public(host):
        return "93.184.216.34"

    monkeypatch.setattr("app.clients.university.public_address", public)
    for status, body in [(200, "x" * 2_000_001), (429, "")]:
        calls = []

        def handler(request, status=status, body=body, calls=calls):
            calls.append(request)
            if request.url.path == "/robots.txt":
                return httpx2.Response(404)
            return httpx2.Response(
                status, text=body, headers={"content-type": "text/html"}
            )

        async with httpx2.AsyncClient(
            transport=httpx2.MockTransport(handler)
        ) as client:
            fetcher = UniversityFetcher(client, HOSTS, NoWait())
            with pytest.raises(CrawlBlocked):
                await fetcher.fetch("https://oist.jp/lab")
            if status == 429:
                with pytest.raises(CrawlBlocked):
                    await fetcher.fetch("https://oist.jp/another-lab")
                assert len(calls) == 2


@pytest.mark.anyio
async def test_full_directory_queue_keeps_later_publication_links():
    class Directories:
        async def fetch(self, url):
            if url.endswith("/publications.html"):
                return FetchedPage(url, "".join(citation(i) for i in range(20)))
            if url == "https://pub.ista.ac.at/~chl/index.html":
                return FetchedPage(url, '<a href="publications.html">Publications</a>')
            return FetchedPage(
                url,
                "".join(
                    f'<p><a href="{url.rstrip("/")}/research-{i}">Learning</a></p>'
                    for i in range(80)
                ),
            )

    snapshots = [
        s
        async for s in scan_pages(
            UniversityScanRequest(query="machine learning", target=20), Directories()
        )
    ]
    assert snapshots[-1].state == "complete"
    assert snapshots[-1].pages_attempted <= 40


def test_automatic_sources_respect_region_and_reviewed_registry():
    from app.services.university_sources import selected_sources

    assert len(selected_sources("both", None)) == 7
    assert set(selected_sources("india", None)) == {"iitgn", "iitk", "iisc"}
    assert set(selected_sources("international", None)) == {
        "oist",
        "kaust",
        "ista",
        "epfl",
    }
    assert selected_sources("india", ["oist", "iitk"]) == ["iitk"]
    request = UniversityScanRequest(query="robotics")
    assert request.universities is None
    assert request.region == "both"
