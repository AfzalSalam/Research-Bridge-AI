from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from datetime import date, datetime
from html.parser import HTMLParser

from app.db.models.enums import AvailabilityStatus, FundingStatus, WorkMode
from app.providers.opportunities import NormalizedOpportunity, RawOpportunityRecord

POLICY_VERSION = "opportunity-title-signals.v1"
_BLOCK_TAGS = {
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "ol",
    "p",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}
_INCLUSION_SIGNALS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("research-internship", re.compile(r"\bresearch\s+intern(?:ship)?\b", re.I)),
    ("internship", re.compile(r"\binternship\b", re.I)),
    ("studentship", re.compile(r"\bstudentship\b", re.I)),
    ("research-assistantship", re.compile(r"\bresearch\s+assistant(?:ship)?\b", re.I)),
    ("fellowship", re.compile(r"\b(?:research\s+)?fellowship\b", re.I)),
    ("phd-student", re.compile(r"\bph\.?d\.?\s+(?:student|candidate)\b", re.I)),
)
_US_REGION_CODES = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "DC",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
}
_COUNTRY_NAMES = {
    "australia": "AU",
    "belgium": "BE",
    "bulgaria": "BG",
    "canada": "CA",
    "france": "FR",
    "germany": "DE",
    "india": "IN",
    "netherlands": "NL",
    "serbia": "RS",
    "singapore": "SG",
    "switzerland": "CH",
    "united kingdom": "GB",
    "united states": "US",
    "usa": "US",
}
_DATE_FORMATS = ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y")


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.casefold() in {"script", "style"}:
            self.ignored_depth += 1
            return
        if self.ignored_depth:
            return
        if tag.casefold() in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style"} and self.ignored_depth:
            self.ignored_depth -= 1
            return
        if self.ignored_depth:
            return
        if tag.casefold() in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth:
            self.parts.append(data)


def normalize_board_record(
    record: RawOpportunityRecord,
    *,
    source_key: str,
    organisation: str,
    retrieved_at: datetime,
) -> NormalizedOpportunity | None:
    """Admit and normalize one record using explicit deterministic evidence."""

    signal = _inclusion_signal(record.title)
    if signal is None:
        return None
    plain_text = html_to_plain_text(record.content)
    evidence: list[dict[str, str]] = [
        {"field": "inclusion", "value": f"{POLICY_VERSION}:{signal}"}
    ]
    duration = _extract_labelled_value(plain_text, ("duration", "length"), 160)
    if duration:
        evidence.append({"field": "duration", "value": duration})
    eligibility = _extract_eligibility(plain_text)
    if eligibility:
        evidence.append({"field": "eligibility", "value": eligibility})
    deadline = _extract_deadline(plain_text)
    if deadline:
        evidence.append({"field": "deadline", "value": deadline.isoformat()})
    work_mode = _extract_work_mode(record.location, plain_text)
    if work_mode is not WorkMode.UNKNOWN:
        evidence.append({"field": "workMode", "value": work_mode.value})
    funding = _extract_funding(plain_text)
    if funding is not FundingStatus.UNKNOWN:
        evidence.append({"field": "funding", "value": funding.value})
    country_code = _country_code(record.location)
    if country_code:
        evidence.append({"field": "countryCode", "value": country_code})

    description = _excerpt(plain_text, 1_200) or "No description was supplied."
    fields = tuple(dict.fromkeys(value for value in record.departments if value))
    search_text = normalize_text(
        " ".join((record.title, plain_text, record.location, *fields))
    ).casefold()
    content_hash = hashlib.sha256(
        json.dumps(
            {
                "applicationUrl": record.absolute_url,
                "departments": fields,
                "description": description,
                "location": record.location,
                "title": record.title,
                "updatedAt": record.updated_at.isoformat(),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return NormalizedOpportunity(
        source_name="Greenhouse",
        source_record_id=f"{source_key}:{record.id}",
        source_kind="official-ats",
        evidence_confidence="high",
        opportunity_type=_opportunity_type(signal),
        title=normalize_text(record.title)[:240],
        organisation=organisation,
        description=description,
        research_fields=fields,
        duration_text=duration,
        eligibility_text=eligibility,
        country_code=country_code,
        location=normalize_text(record.location)[:240] or None,
        work_mode=work_mode,
        funding=funding,
        availability=AvailabilityStatus.OPEN,
        deadline=deadline,
        source_url=record.absolute_url,
        application_url=record.absolute_url,
        source_updated_at=record.updated_at,
        last_verified_at=retrieved_at,
        extraction_evidence=tuple(evidence),
        inclusion_signal=signal,
        search_text=search_text,
        content_hash=content_hash,
    )


def html_to_plain_text(value: str) -> str:
    """Convert provider HTML to bounded normalized plain text, never markup."""

    parser = _PlainTextParser()
    parser.feed(html.unescape(value[:250_000]))
    parser.close()
    lines = []
    for line in "".join(parser.parts).splitlines():
        normalized = normalize_text(line)
        if normalized:
            lines.append(normalized)
    return "\n".join(lines)[:20_000]


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(
        "".join(
            character
            for character in normalized
            if character >= " " or character == "\n"
        ).split()
    )


def matches_query(opportunity: NormalizedOpportunity, query: str) -> bool:
    tokens = [token for token in normalize_text(query).casefold().split() if token]
    return all(token in opportunity.search_text for token in tokens)


def _inclusion_signal(title: str) -> str | None:
    for label, pattern in _INCLUSION_SIGNALS:
        if pattern.search(title):
            return label
    return None


def _opportunity_type(signal: str) -> str:
    return {
        "studentship": "studentship",
        "research-assistantship": "research-assistantship",
        "fellowship": "fellowship",
        "phd-student": "studentship",
    }.get(signal, "internship")


def _extract_labelled_value(
    text: str, labels: tuple[str, ...], maximum: int
) -> str | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"^(?:{label_pattern})\s*:?\s*(?P<value>[^\n]{{2,{maximum}}})$",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    return normalize_text(match.group("value"))[:maximum] if match else None


def _extract_eligibility(text: str) -> str | None:
    lines = text.splitlines()
    headings = {"requirements", "qualifications", "who you are", "eligibility"}
    for index, line in enumerate(lines):
        normalized = line.rstrip(":").casefold()
        if normalized not in headings:
            continue
        excerpt = _excerpt(" ".join(lines[index + 1 : index + 5]), 600)
        if excerpt:
            return excerpt
    return None


def _extract_deadline(text: str) -> date | None:
    value = _extract_labelled_value(
        text, ("application deadline", "deadline", "apply by"), 80
    )
    if value is None:
        return None
    candidates = [value]
    candidates.extend(
        match.group(0)
        for match in re.finditer(
            r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2} [A-Za-z]+ \d{4}|"
            r"[A-Za-z]+ \d{1,2}, \d{4})\b",
            value,
        )
    )
    for candidate in reversed(candidates):
        for date_format in _DATE_FORMATS:
            try:
                return datetime.strptime(candidate.strip(), date_format).date()
            except ValueError:
                continue
    return None


def _extract_work_mode(location: str, text: str) -> WorkMode:
    location_value = location.casefold()
    if "hybrid" in location_value and not _is_negated_mode(location_value, "hybrid"):
        return WorkMode.HYBRID
    if "remote" in location_value and not _is_negated_mode(location_value, "remote"):
        return WorkMode.REMOTE
    content = text.casefold()
    if re.search(r"\bhybrid\b", content) and not _is_negated_mode(content, "hybrid"):
        return WorkMode.HYBRID
    remote = bool(re.search(r"\bremote(?:ly)?\b", content)) and not _is_negated_mode(
        content, "remote"
    )
    on_site = bool(re.search(r"\b(?:on[- ]site|in[- ]person)\b", content))
    if remote == on_site:
        return WorkMode.UNKNOWN
    return WorkMode.REMOTE if remote else WorkMode.ON_SITE


def _is_negated_mode(content: str, mode: str) -> bool:
    escaped = re.escape(mode)
    return bool(
        re.search(
            rf"\b(?:not|no)\s+(?:an?\s+)?(?:fully\s+)?{escaped}\b|"
            rf"\b{escaped}(?:\s+(?:work|position|role))?\s+(?:is\s+)?not\b|"
            rf"\b(?:do|does)\s+not\s+(?:allow|offer|support)\s+{escaped}\b",
            content,
        )
    )


def _extract_funding(text: str) -> FundingStatus:
    content = text.casefold()
    if re.search(r"\b(?:unpaid|without compensation)\b", content):
        return FundingStatus.UNFUNDED
    funded = bool(
        re.search(
            r"\b(?:paid internship|compensation|salary|stipend|hourly rate)\b|"
            r"(?:[$€£]\s?\d)",
            content,
        )
    )
    return FundingStatus.FUNDED if funded else FundingStatus.UNKNOWN


def _country_code(location: str) -> str | None:
    lowered = location.casefold()
    for name, code in _COUNTRY_NAMES.items():
        if re.search(rf"\b{re.escape(name)}\b", lowered):
            return code
    parts = [part.strip() for part in location.split(",")]
    if parts and parts[-1].upper() in _US_REGION_CODES:
        return "US"
    return None


def _excerpt(value: str, maximum: int) -> str | None:
    normalized = normalize_text(value)
    if not normalized:
        return None
    if len(normalized) <= maximum:
        return normalized
    prefix = normalized[: maximum - 1].rsplit(" ", 1)[0].rstrip()
    return f"{prefix}…"
