"""Resolve registry-owned official domains; never derive trust from user URLs."""

import asyncio
import re
import time
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, Field, ValidationError


class RegistryUnavailable(Exception):
    pass


class RegistryLink(BaseModel):
    type: str
    value: str


class RegistryName(BaseModel):
    value: str
    types: list[str] = Field(default_factory=list)


class RegistryRecord(BaseModel):
    id: str
    status: str
    names: list[RegistryName]
    links: list[RegistryLink]
    domains: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class OfficialInstitution:
    ror_id: str
    name: str
    website: str
    hosts: frozenset[str]


def valid_domain(host: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host)) and (
        "." in host
        and ".." not in host
        and not host.replace(".", "").isdigit()
        and host
        not in {
            "co.uk",
            "ac.uk",
            "ac.in",
            "edu.in",
            "com.au",
            "edu.au",
            "github.io",
            "wordpress.com",
            "blogspot.com",
        }
        and not host.endswith((".localhost", ".local", ".test", ".invalid", ".example"))
    )


def official_institution(
    record: RegistryRecord, identifier: str
) -> OfficialInstitution | None:
    if (
        record.id.rstrip("/") != f"https://ror.org/{identifier}"
        or record.status != "active"
    ):
        return None
    if not set(record.types) & {"education", "nonprofit", "facility", "government"}:
        return None
    website = next(
        (link.value for link in record.links if link.type == "website"), None
    )
    if not website:
        return None
    try:
        parts = urlsplit(website)
        if (
            parts.scheme not in {"https", "http"}
            or parts.username
            or parts.password
            or parts.port not in {None, 80, 443}
        ):
            return None
        host = (parts.hostname or "").lower().removeprefix("www.")
        if not valid_domain(host):
            return None
    except ValueError:
        return None
    hosts = {host}
    for domain in record.domains:
        domain = domain.lower().removeprefix("www.")
        if valid_domain(domain):
            hosts.add(domain)
    name = next(
        (name.value for name in record.names if "ror_display" in name.types),
        record.names[0].value if record.names else identifier,
    )
    return OfficialInstitution(
        record.id,
        name,
        urlunsplit(("https", parts.hostname or "", parts.path or "/", "", "")),
        frozenset(hosts),
    )


class InstitutionRegistry:
    def __init__(self) -> None:
        self.cache: dict[str, tuple[float, OfficialInstitution | None]] = {}

    async def resolve(self, ror_id: str) -> OfficialInstitution | None:
        identifier = (
            ror_id.rstrip("/")
            .removeprefix("https://ror.org/")
            .removeprefix("http://ror.org/")
        )
        if not re.fullmatch(r"0[a-z0-9]{8}", identifier):
            return None
        cached = self.cache.get(identifier)
        if cached and time.monotonic() - cached[0] < 86400:
            return cached[1]
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(5, connect=3), follow_redirects=False, trust_env=False
        ) as client:
            for attempt in range(2):
                try:
                    response = await client.get(
                        f"https://api.ror.org/v2/organizations/{identifier}"
                    )
                    if response.status_code == 404:
                        resolved = None
                    else:
                        response.raise_for_status()
                        resolved = official_institution(
                            RegistryRecord.model_validate(response.json()), identifier
                        )
                    if len(self.cache) >= 1000:
                        self.cache.pop(next(iter(self.cache)))
                    self.cache[identifier] = (time.monotonic(), resolved)
                    return resolved
                except httpx.HTTPStatusError as error:
                    if error.response.status_code == 429:
                        raise RegistryUnavailable(
                            "Institution registry is rate limited; try later."
                        ) from error
                    if attempt or error.response.status_code < 500:
                        raise RegistryUnavailable(
                            "Official institution metadata is unavailable."
                        ) from error
                except (httpx.HTTPError, ValidationError, ValueError) as error:
                    if attempt:
                        raise RegistryUnavailable(
                            "Official institution metadata could not be validated."
                        ) from error
                await asyncio.sleep(0.25)
        return None
