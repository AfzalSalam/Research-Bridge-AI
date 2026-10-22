"""Conservative public-email extraction and deterministic identity corroboration."""

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

from app.repositories.contact import ContactIdentity

EMAIL = re.compile(
    r"(?<![\w.+-])[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9.-]*[A-Z0-9])?\.[A-Z]{2,24}(?![\w.-])",
    re.I,
)
GENERIC = {
    "info",
    "admin",
    "administrator",
    "office",
    "contact",
    "support",
    "webmaster",
    "admissions",
    "help",
    "noreply",
    "no-reply",
    "recruitment",
    "secretary",
    "enquiries",
}


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return " ".join(
        re.findall(
            r"[^\W_]+", "".join(c for c in value if not unicodedata.combining(c))
        )
    )


def name_matches(name: str, text: str) -> bool:
    parts = [p for p in normalized(name).split() if len(p) > 1]
    words = normalized(text).split()
    # Short initials alone cannot distinguish namesakes. Preserve word boundaries.
    return len(parts) >= 2 and all(p in words for p in parts)


def document(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup.select(
        "script, style, noscript, footer, nav, [hidden], [aria-hidden='true']"
    ):
        element.decompose()
    return soup


def personal_page(identity: ContactIdentity, soup: BeautifulSoup) -> bool:
    return any(
        name_matches(identity.name, tag.get_text(" ", strip=True))
        for tag in soup.select("title, h1")
    )


def corroboration(identity: ContactIdentity, soup: BeautifulSoup) -> list[str]:
    links = [
        unquote(str(a.get("href", ""))).casefold().rstrip("/")
        for a in soup.select("a[href]")
    ]
    safe_links = []
    for link in links:
        try:
            urlsplit(link)
        except ValueError:
            continue
        safe_links.append(link)
    links = safe_links
    text = normalized(soup.get_text(" ", strip=True))
    evidence: list[str] = []
    if identity.orcid:
        identifier = identity.orcid.rstrip("/").split("/")[-1].casefold()
        if any(
            urlsplit(link).hostname in {"orcid.org", "www.orcid.org"}
            and urlsplit(link).path.strip("/") == identifier
            for link in links
        ):
            evidence.append("ORCID matches the stored author identifier")
    for title, doi in identity.papers:
        doi_value = (doi or "").lower().removeprefix("https://doi.org/")
        exact_doi = bool(doi_value) and any(
            urlsplit(link).hostname in {"doi.org", "dx.doi.org"}
            and urlsplit(link).path.lstrip("/") == doi_value
            for link in links
        )
        title_value = normalized(title)
        if exact_doi or (len(title_value) >= 25 and f" {title_value} " in f" {text} "):
            evidence.append("Stored publication matches: " + title[:240])
            break
    return evidence


@dataclass(frozen=True)
class ExtractedEmail:
    email: str
    extraction: str


def public_emails(
    soup: BeautifulSoup, identity: ContactIdentity
) -> list[ExtractedEmail]:
    found: dict[str, ExtractedEmail] = {}
    # Small local blocks avoid attributing an assistant's or a footer's address.
    for node in soup.find_all(["a", "p", "td", "li", "div", "address", "span"]):
        visible = node.get_text(" ", strip=True)
        if len(visible) > 500:
            continue
        context = node.parent.get_text(" ", strip=True) if node.parent else visible
        if re.search(
            r"\b(?:personal assistant|administrative assistant|secretary|"
            r"webmaster|administration|web\s*design)\b",
            context[:700],
            re.I,
        ):
            continue
        href = str(node.get("href", ""))
        kind = "mailto" if href.lower().startswith("mailto:") else "text"
        value = unquote(href[7:].split("?", 1)[0]) if kind == "mailto" else visible
        decoded = re.sub(r"\s*(?:\[at\]|\(at\)|\{at\})\s*", "@", value, flags=re.I)
        decoded = re.sub(r"\s+(?:at)\s+", "@", decoded, flags=re.I)
        decoded = re.sub(r"\s*(?:\[dot\]|\(dot\)|\{dot\})\s*", ".", decoded, flags=re.I)
        decoded = re.sub(r"\s+dot\s+", ".", decoded, flags=re.I)
        if decoded != value and kind != "mailto":
            kind = "obfuscated"
        for match in EMAIL.finditer(decoded):
            email = match.group().strip(".").lower()
            local, host = email.rsplit("@", 1)
            if (
                local in GENERIC
                or any(
                    x in local
                    for x in ("initial", "firstname", "lastname", "username", "example")
                )
                or ".." in email
                or len(email) > 254
                or len(local) > 64
                or host in {"example.com", "example.org", "example.edu"}
            ):
                continue
            name_parts = normalized(identity.name).split()
            compact_local = re.sub(r"[^a-z0-9]", "", local)
            initials = "".join(part[0] for part in name_parts)
            attributable = any(
                part in compact_local for part in name_parts if len(part) >= 3
            )
            attributable = attributable or (
                len(initials) >= 2 and compact_local == initials
            )
            if not attributable:
                continue
            if email not in found or kind == "mailto":
                found[email] = ExtractedEmail(email, kind)
    return list(found.values())
