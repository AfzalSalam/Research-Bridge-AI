"""Conservative publication and program evidence extraction, without LLM inference."""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from app.clients.university import CrawlBlocked, approved_url
from app.schemas.university import UniversityProgram, WebsitePaper, WorkMode
from app.services.university_sources import UniversitySource

STOP_WORDS = frozenset(
    [
        "the",
        "and",
        "for",
        "with",
        "from",
        "research",
        "papers",
        "paper",
        "internship",
        "internships",
        "students",
        "student",
        "university",
        "recent",
        "latest",
        "about",
        "using",
        "based",
        "applications",
        "in",
        "on",
        "of",
        "to",
        "a",
        "an",
    ]
)
DOI = re.compile(r"10\.\d{4,9}/[^\s<>\"]+", re.I)
DATE = re.compile(
    r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s*,?\s*\d{4}|[A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})\b"
)


def clean(text: str) -> str:
    return " ".join(text.split())


def terms(query: str) -> list[str]:
    query = re.sub(r"\bAI\b", "artificial intelligence", query, flags=re.I)
    query = re.sub(r"\bML\b", "machine learning", query, flags=re.I)
    return sorted(set(re.findall(r"[^\W_]{3,}", query.casefold())) - STOP_WORDS)


def matches(text: str, query_terms: list[str]) -> list[str]:
    words = set(re.findall(r"[^\W_]{3,}", text.casefold()))
    return [term for term in query_terms if term in words]


def parsed_date(text: str) -> date | None:
    match = DATE.search(text)
    if not match:
        return None
    value = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", match[0], flags=re.I)
    value = clean(value.replace(",", ""))
    for fmt in ("%B %d %Y", "%d %B %Y", "%b %d %Y", "%d %b %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def document(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select("script, style, nav, footer, header, noscript, form"):
        tag.decompose()
    return soup


def safe_publication_link(url: str) -> bool:
    try:
        parts = urlsplit(url)
        return bool(
            parts.scheme == "https"
            and parts.hostname
            and not parts.username
            and not parts.password
            and parts.port in (None, 443)
            and "\\" not in url
            and len(url) <= 1800
        )
    except ValueError:
        return False


def extract_papers(
    soup: BeautifulSoup,
    url: str,
    university: str,
    query_terms: list[str],
    now: datetime,
) -> list[WebsitePaper]:
    records: list[tuple[str | None, str, str, str | None]] = []
    metadata = soup.find("meta", attrs={"name": "citation_title"})
    if isinstance(metadata, Tag):
        title: str | None = clean(str(metadata.get("content", "")))
        doi_meta = soup.find("meta", attrs={"name": "citation_doi"})
        raw_doi = str(doi_meta.get("content", "")) if isinstance(doi_meta, Tag) else ""
        found = DOI.search(raw_doi)
        doi = found[0].rstrip(".,;)").lower() if found else None
        if title:
            records.append(
                (title, title, "https://doi.org/" + doi if doi else url, doi)
            )
    for anchor in soup.find_all("a", href=True):
        try:
            href = urljoin(url, str(anchor["href"]))
            host = urlsplit(href).hostname or ""
        except ValueError:
            continue
        found = DOI.search(unquote(href)) if host in {"doi.org", "dx.doi.org"} else None
        arxiv = host in {"arxiv.org", "www.arxiv.org"} and "/abs/" in href
        if not found and not arxiv:
            continue
        parent = anchor.find_parent(["li", "p", "tr", "article"])
        citation = clean(
            parent.get_text(" ", strip=True) if parent else anchor.get_text(" ")
        )
        if not 20 <= len(citation) <= 2200:
            continue
        label = clean(anchor.get_text(" ", strip=True))
        # A full citation is preserved as a citation, never relabelled a paper title.
        title = (
            label if len(label.split()) >= 4 and not label.startswith("http") else None
        )
        doi = found[0].rstrip(".,;)").lower() if found else None
        records.append(
            (title, citation, "https://doi.org/" + doi if doi else href, doi)
        )
    result = []
    for title, citation, link, doi in records:
        matched = matches(citation, query_terms)
        if not query_terms or len(matched) / len(query_terms) < 0.5:
            continue
        if not safe_publication_link(link):
            continue
        parts = urlsplit(link)
        arxiv_key = (
            "arxiv:" + re.sub(r"v\d+$", "", parts.path.removeprefix("/abs/"))
            if parts.hostname in {"arxiv.org", "www.arxiv.org"}
            else None
        )
        key = doi or arxiv_key or clean(title or citation).casefold()
        result.append(
            WebsitePaper(
                id=hashlib.sha256(key.encode()).hexdigest()[:20],
                university=university,
                title=title,
                citation=citation,
                doi=doi,
                publication_url=link,
                source_url=url,
                checked_at=now,
                matched_terms=matched,
            )
        )
    return result


def crawl_links(
    soup: BeautifulSoup, url: str, source: UniversitySource, query_terms: list[str]
) -> list[tuple[int, str]]:
    links: dict[str, int] = {}
    for anchor in soup.find_all("a", href=True):
        try:
            candidate_url = urljoin(url, str(anchor["href"]))
            if candidate_url.startswith("http://"):
                candidate_url = "https://" + candidate_url[7:]
            href = approved_url(candidate_url, source.hosts)
        except (CrawlBlocked, ValueError):
            continue
        if re.search(r"\.(pdf|jpg|png|zip|bib|xml|mp4|docx?)$", href, re.I):
            continue
        label = clean(anchor.get_text(" ", strip=True))
        context = label
        # Small faculty cards carry research topics; a whole directory does not
        # establish relevance for every link within it.
        for ancestor in list(anchor.parents)[:3]:
            candidate = clean(ancestor.get_text(" ", strip=True))
            if len(candidate) > 600:
                break
            if len(candidate) > len(label) + 20:
                context = candidate
                break
        path_words = re.sub(r"[-_/]", " ", urlsplit(href).path)
        direct_matches = matches(label + " " + path_words, query_terms)
        matched = matches(context, query_terms)
        research_link = re.search(
            r"publications?|papers?|research|faculty|people|members|labs?|groups?|units?|internship|fellowship",
            label + " " + urlsplit(href).path,
            re.I,
        )
        if not matched and not research_link:
            continue
        priority = (
            len(direct_matches) * 30
            + len(matched) * 10
            + (100 if re.search(r"publication|papers", label + href, re.I) else 0)
        )
        links[href] = max(priority, links.get(href, 0))
    return sorted(((score, link) for link, score in links.items()), reverse=True)[:80]


def work_mode(blocks: list[str]) -> tuple[WorkMode, str | None]:
    findings: dict[WorkMode, str] = {}
    for block in blocks:
        if not re.search(r"\bintern(?:s|ship|ships)?\b", block, re.I):
            continue
        if re.search(r"\b(not|no|cannot|unavailable|previous|formerly)\b", block, re.I):
            continue
        patterns: dict[WorkMode, str] = {
            "remote": (
                r"remote internship|interns? (?:may |can |will )?work remotely"
                r"|internship[^.]{0,45}(?:fully remote|remote work)"
            ),
            "on-site": (
                r"(?:on[- ]site|in[- ]person) internships?"
                r"|internship[^.]{0,45}(?:conducted|held|offered|undertaken)"
                r"[^.]{0,20}(?:on[- ]site|in[- ]person|offline mode)"
                r"|interns? (?:must|will) (?:work|be present) on[- ]site"
            ),
            "hybrid": (
                r"hybrid (?:internship|work|arrangement)"
                r"|internship[^.]{0,35}hybrid"
            ),
        }
        for mode, pattern in patterns.items():
            if re.search(pattern, block, re.I):
                findings[mode] = block[:800]
    if len(findings) == 1:
        return next(iter(findings.items()))
    return "not-specified", None


def extract_program(
    soup: BeautifulSoup, source: UniversitySource, url: str, now: datetime
) -> UniversityProgram:
    blocks = [clean(tag.get_text(" ", strip=True)) for tag in soup.select("p, li, tr")]
    blocks = [block for block in blocks if 10 <= len(block) <= 2500]
    status: str = "not-confirmed"
    evidence: str | None = None
    deadline: str | None = None
    dates: list[tuple[date, str]] = []
    # Prefer explicitly labelled deadline columns, never internship start dates.
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [
            clean(cell.get_text(" ")).lower() for cell in rows[0].find_all(["th", "td"])
        ]
        indexes = [i for i, text in enumerate(headers) if "deadline" in text]
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            for i in indexes:
                if i < len(cells):
                    parsed = parsed_date(cells[i].get_text(" "))
                    if parsed:
                        dates.append((parsed, clean(row.get_text(" "))[:800]))
    for block in blocks:
        if re.search(
            r"last date.*applications|application deadline"
            r"|deadline.*(?:apply|application)",
            block,
            re.I,
        ):
            parsed = parsed_date(block)
            if parsed:
                dates.append((parsed, block[:800]))
        if re.search(
            r"applications? (?:are )?accepted on a continuous basis"
            r"|application deadlines?:? all year round",
            block,
            re.I,
        ):
            status, evidence = "rolling", block[:800]
    if dates:
        future = [item for item in dates if item[0] >= now.date()]
        chosen = min(future) if future else max(dates)
        status, deadline, evidence = (
            ("open" if future else "closed"),
            chosen[0].isoformat(),
            chosen[1],
        )
    closed = next(
        (
            b
            for b in blocks
            if re.search(
                r"applications? (?:form )?(?:are |is )?(?:now )?closed"
                r"|no longer accepting applications",
                b,
                re.I,
            )
        ),
        None,
    )
    if closed:
        status, evidence = "closed", closed[:800]
    mode, mode_evidence = work_mode(blocks)
    eligibility = next(
        (
            b[:800]
            for b in blocks
            if re.search(
                r"eligib|students.*(?:bachelor|master)|students.*institut.*india",
                b,
                re.I,
            )
        ),
        None,
    )
    # Pydantic validates the status values; no generated or inferred numeric scores.
    return UniversityProgram.model_validate(
        {
            "university": source.name,
            "name": source.program_name,
            "source_url": url,
            "checked_at": now,
            "status": status,
            "deadline": deadline,
            "status_evidence": evidence,
            "work_mode": mode,
            "work_mode_evidence": mode_evidence,
            "eligibility_evidence": eligibility,
            "application_note": source.application_note,
        }
    )
