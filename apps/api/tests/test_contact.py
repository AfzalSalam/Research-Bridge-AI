import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.clients.university import CrawlBlocked, FetchedPage
from app.core.config import Settings
from app.core.errors import AppError
from app.main import create_app
from app.repositories.contact import ContactIdentity
from app.schemas.contact import ContactLookupRequest, ContactLookupResponse
from app.services.contact import ContactService, crawl_contact, lookup_sources
from app.services.contact_extraction import document, name_matches, public_emails
from app.services.university_scan import UniversityScanService
from tests.auth_support import StaticAccessTokenVerifier, account_profile_payload
from tests.test_mentor_discovery import RepeatedAuthorProvider


@pytest.fixture
def anyio_backend():
    return "asyncio"


IDENTITY = ContactIdentity(
    uuid4(),
    "Mira Sen",
    "https://orcid.org/0000-0001-1234-5678",
    ("Indian Institute of Technology Kanpur",),
    (("Reliable machine learning for clinical decision support", "10.1234/paper"),),
)
PROFILE = "https://www.cse.iitk.ac.in/users/mira/"
HTML = (
    "<title>Mira Sen | Faculty</title><h1>Mira Sen</h1>"
    '<p>Email: <a href="mailto:mira.sen@iitk.ac.in">Email</a></p>'
    '<a href="https://orcid.org/0000-0001-1234-5678">ORCID</a>'
)


@pytest.mark.parametrize(
    "address,kind",
    [
        ('<a href="mailto:mira.sen@iitk.ac.in?subject=Hello">Email</a>', "mailto"),
        ("<p>mira.sen [at] iitk [dot] ac [dot] in</p>", "obfuscated"),
        ("<p>mira.sen (at) iitk (dot) ac (dot) in</p>", "obfuscated"),
        ("<p>mira.sen@iitk.ac.in</p>", "text"),
    ],
)
def test_public_formats(address, kind):
    emails = public_emails(document(address), IDENTITY)
    assert len(emails) == 1
    assert emails[0].email == "mira.sen@iitk.ac.in"
    assert emails[0].extraction == kind


@pytest.mark.parametrize(
    "html",
    [
        "<footer>mira.sen@iitk.ac.in</footer>",
        "<p>info@iitk.ac.in</p>",
        "<p>my_initials [at] iitk [dot] ac [dot] in</p>",
        "<p>Personal assistant: mira.sen@iitk.ac.in</p>",
        "<p>someone.else@iitk.ac.in</p>",
        "<script>mira.sen@iitk.ac.in</script>",
        "<p hidden>mira.sen@iitk.ac.in</p>",
    ],
)
def test_no_footer_generic_placeholder_or_other_person_address(html):
    assert public_emails(document(html), IDENTITY) == []


def test_names_preserve_word_boundaries_and_full_names():
    assert not name_matches("Mira Sen", "Miranda Senn")
    assert not name_matches("M. Sen", "Mira Sen")
    assert name_matches("Mira Sen", "Professor Mira H. Sen")
    assert name_matches("José García", "Jose Garcia")


@pytest.mark.anyio
async def test_directory_to_matched_profile():
    fetcher = AsyncMock()
    fetcher.fetch.side_effect = lambda url: FetchedPage(
        url, HTML if url == PROFILE else f'<nav><a href="{PROFILE}">Mira Sen</a></nav>'
    )
    result = await crawl_contact(IDENTITY, None, fetcher)
    assert result.status == "found"
    assert len(result.emails) == 1
    assert result.emails[0].source_url == PROFILE
    assert result.pages_checked == 2
    assert "ORCID" in result.emails[0].identity_evidence[1]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "html",
    [
        HTML.replace("0000-0001-1234-5678", "0000-0009-9999-9999"),
        HTML.replace(
            "<title>Mira Sen | Faculty</title><h1>Mira Sen</h1>",
            "<title>Faculty directory</title><h1>Our team</h1>",
        ),
        HTML.replace("mira.sen@iitk.ac.in", "somebody.else@iitk.ac.in"),
    ],
)
async def test_identity_or_attribution_mismatch_never_offers_email(html):
    fetcher = AsyncMock()
    fetcher.fetch.return_value = FetchedPage(PROFILE, html)
    result = await crawl_contact(IDENTITY, PROFILE, fetcher)
    assert result.status != "found"
    assert not result.emails


@pytest.mark.anyio
async def test_publication_identity_and_same_mailbox_aliases():
    fetcher = AsyncMock()
    html = HTML.replace(
        "https://orcid.org/0000-0001-1234-5678", "https://doi.org/10.1234/paper"
    )
    html += "<p>mira.sen@cse.iitk.ac.in</p>"
    fetcher.fetch.return_value = FetchedPage(PROFILE, html)
    result = await crawl_contact(IDENTITY, PROFILE, fetcher)
    assert result.status == "found"
    assert len(result.emails) == 2
    assert "publication" in result.emails[0].identity_evidence[1]


@pytest.mark.anyio
async def test_different_mailboxes_and_wrong_doi_suffix_need_review():
    fetcher = AsyncMock()
    fetcher.fetch.return_value = FetchedPage(
        PROFILE, HTML + "<p>mira.other@iitk.ac.in</p>"
    )
    assert (await crawl_contact(IDENTITY, PROFILE, fetcher)).status == "needs-review"
    html = HTML.replace(
        "https://orcid.org/0000-0001-1234-5678",
        "https://doi.org/10.1234/paper-impostor",
    )
    fetcher.fetch.return_value = FetchedPage(PROFILE, html)
    assert (await crawl_contact(IDENTITY, PROFILE, fetcher)).status == "needs-review"


@pytest.mark.anyio
async def test_crawl_boundaries_and_unsupported_affiliation():
    fetcher = AsyncMock()
    fetcher.fetch.return_value = FetchedPage(
        PROFILE,
        '<a href="https://evil.test/profile">Mira Sen</a>'
        '<a href="https://[bad">Mira Sen</a>',
    )
    assert (await crawl_contact(IDENTITY, PROFILE, fetcher)).status == "not-found"
    assert fetcher.fetch.await_count == 1
    fetcher.fetch.side_effect = CrawlBlocked("Robots denied")
    result = await crawl_contact(IDENTITY, PROFILE, fetcher)
    assert result.status == "blocked"
    assert "Robots denied" in result.warnings[0]
    identity = replace(IDENTITY, affiliations=("Unreviewed University",))
    assert (await crawl_contact(identity, None, fetcher)).status == "unsupported"


@pytest.mark.anyio
async def test_budget_and_cancel_release_concurrency(monkeypatch):
    fetcher = AsyncMock()

    async def slow(_url):
        await asyncio.sleep(10)

    fetcher.fetch.side_effect = slow
    assert (
        await crawl_contact(IDENTITY, PROFILE, fetcher, budget=0.01)
    ).status == "blocked"
    repository = AsyncMock()
    repository.identity.return_value = IDENTITY
    repository.cached.return_value = None
    monkeypatch.setattr(
        "app.services.contact.crawl_contact",
        AsyncMock(side_effect=asyncio.CancelledError),
    )
    scanner = UniversityScanService()
    service = ContactService(repository, scanner)
    with pytest.raises(asyncio.CancelledError):
        await service.lookup(IDENTITY.id, uuid4(), ContactLookupRequest())
    assert scanner.active_owners == {}
    repository.save.assert_not_awaited()


@pytest.mark.anyio
async def test_cache_expiry_recheck_and_rejected_url(monkeypatch):
    result = ContactLookupResponse(
        author_id=IDENTITY.id,
        author_name=IDENTITY.name,
        status="not-found",
        checked_at=datetime.now(UTC),
    )
    repository = AsyncMock()
    repository.identity.return_value = IDENTITY
    repository.cached.return_value = result
    crawl = AsyncMock(return_value=result)
    monkeypatch.setattr("app.services.contact.crawl_contact", crawl)
    service = ContactService(repository, UniversityScanService())
    assert (
        await service.lookup(IDENTITY.id, uuid4(), ContactLookupRequest())
    ).cache_hit
    crawl.assert_not_awaited()
    await service.lookup(IDENTITY.id, uuid4(), ContactLookupRequest(refresh=True))
    assert crawl.await_count == 1
    repository.cached.return_value = result.model_copy(
        update={"checked_at": datetime.now(UTC) - timedelta(hours=2)}
    )
    await service.lookup(IDENTITY.id, uuid4(), ContactLookupRequest())
    assert crawl.await_count == 2
    with pytest.raises(AppError) as error:
        await service.lookup(
            IDENTITY.id,
            uuid4(),
            ContactLookupRequest(profile_url="https://127.0.0.1/private"),
        )
    assert error.value.status_code == 422


def test_authenticated_api_persistence(migrated_database_url, monkeypatch):
    app = create_app(
        Settings(
            app_environment="test",
            database_url=migrated_database_url,
            log_level="CRITICAL",
        )
    )
    app.state.institution_registry.resolve = AsyncMock(return_value=None)
    app.state.paper_provider_override = RepeatedAuthorProvider()
    app.state.auth_verifier_override = StaticAccessTokenVerifier(
        {"contact-user": "contact-subject"}
    )

    async def crawl(identity, url, _fetcher, **kwargs):
        return ContactLookupResponse(
            author_id=identity.id,
            author_name=identity.name,
            status="not-found",
            checked_at=datetime.now(UTC),
            lookup_url=url,
        )

    mock = AsyncMock(side_effect=crawl)
    monkeypatch.setattr("app.services.contact.crawl_contact", mock)
    with TestClient(app) as client:
        endpoint = f"/api/v1/authors/{uuid4()}/public-email"
        assert client.post(endpoint, json={}).status_code == 401
        client.headers.update({"Authorization": "Bearer contact-user"})
        assert (
            client.put("/api/v1/profile", json=account_profile_payload()).status_code
            == 200
        )
        response = client.post(
            "/api/v1/discovery/mentors", json={"query": "clinical AI"}
        )
        author_id = response.json()["candidates"][0]["id"]
        endpoint = f"/api/v1/authors/{author_id}/public-email"
        first = client.post(endpoint, json={})
        assert first.status_code == 200, first.text
        assert not first.json()["cacheHit"]
        assert client.post(endpoint, json={}).json()["cacheHit"]
        assert mock.await_count == 1
        assert (
            client.post(endpoint, json={"profileUrl": "https://evil.test/"}).status_code
            == 422
        )
        assert (
            client.post(f"/api/v1/authors/{uuid4()}/public-email", json={}).status_code
            == 404
        )


def test_institution_aliases_do_not_match_substrings_or_other_institutes():
    assert (
        lookup_sources(replace(IDENTITY, affiliations=("Pakistan University",))) == []
    )
    assert (
        lookup_sources(
            replace(
                IDENTITY,
                affiliations=("Indian Institute of Science Education and Research",),
            )
        )
        == []
    )
    assert lookup_sources(IDENTITY) == ["iitk"]
