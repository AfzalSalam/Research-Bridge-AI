"""Bounded robots-aware HTTPS fetcher with DNS pinning against SSRF/rebinding."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx2

USER_AGENT = "ResearchBridgeBot"
MAX_BYTES = 2_000_000


class CrawlBlocked(Exception):
    """Safe public reason that a page cannot be fetched."""


def approved_url(url: str, hosts: frozenset[str]) -> str:
    try:
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or not any(
                parts.hostname == h or (parts.hostname or "").endswith("." + h)
                for h in hosts
            )
            or parts.username
            or parts.password
            or parts.port not in (None, 443)
            or any(char.isspace() or ord(char) < 32 for char in url)
            or len(url) > 1800
            or "\\" in url
        ):
            raise ValueError
    except ValueError as error:
        raise CrawlBlocked(
            "Link outside the reviewed HTTPS hosts was skipped."
        ) from error
    # Query URLs can create unbounded calendars/searches; entry points use paths.
    if parts.query:
        raise CrawlBlocked("Query-string crawl links are not supported.")
    return urlunsplit(("https", parts.netloc.lower(), parts.path or "/", "", ""))


async def public_address(host: str) -> str:
    try:
        records = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(
                host,
                443,
                type=socket.SOCK_STREAM,
            ),
            timeout=5,
        )
    except (OSError, TimeoutError) as error:
        raise CrawlBlocked("University hostname could not be resolved.") from error
    addresses = list(dict.fromkeys(str(row[4][0]) for row in records))
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise CrawlBlocked("Non-public network address was blocked.")
    return next((ip for ip in addresses if ":" not in ip), addresses[0])


class HostPacer:
    """Shared per-host pacing across scans in this API process."""

    def __init__(self) -> None:
        self.locks: dict[str, asyncio.Lock] = {}
        self.last: dict[str, float] = {}

    async def wait(self, host: str, delay: float) -> None:
        async with self.locks.setdefault(host, asyncio.Lock()):
            remaining = self.last.get(host, 0) + max(1.0, delay) - time.monotonic()
            if remaining > 0:
                await asyncio.sleep(remaining)
            self.last[host] = time.monotonic()


@dataclass(frozen=True)
class FetchedPage:
    url: str
    html: str


class UniversityFetcher:
    def __init__(
        self, client: httpx2.AsyncClient, hosts: frozenset[str], pacer: HostPacer
    ) -> None:
        self.client = client
        self.hosts = hosts
        self.pacer = pacer
        self.robots: dict[str, RobotFileParser | None] = {}
        self.blocked_hosts: set[str] = set()

    async def _request(self, url: str, delay: float = 1) -> tuple[int, str, str, str]:
        url = approved_url(url, self.hosts)
        host = urlsplit(url).hostname
        assert host is not None
        if host in self.blocked_hosts:
            raise CrawlBlocked(
                "This university requested a pause; no more requests sent."
            )
        await self.pacer.wait(host, delay)
        address = await public_address(host)
        # Pin the vetted IP for the actual connection; preserve TLS verification
        # against the original hostname. Disable keepalive to avoid cross-host reuse.
        pinned = httpx2.URL(url).copy_with(host=address)
        try:
            async with self.client.stream(
                "GET",
                pinned,
                headers={"Host": host, "User-Agent": USER_AGENT, "Connection": "close"},
                extensions={"sni_hostname": host},
            ) as response:
                if response.status_code in (429, 503):
                    self.blocked_hosts.add(host)
                    raise CrawlBlocked(
                        "University rate limit or maintenance; scan paused there."
                    )
                data = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        raise CrawlBlocked("Page exceeds the 2 MB scan limit.")
                return (
                    response.status_code,
                    data.decode("utf-8", errors="replace"),
                    response.headers.get("content-type", ""),
                    response.headers.get("location", ""),
                )
        except httpx2.HTTPError as error:
            raise CrawlBlocked(
                "University page could not be reached securely."
            ) from error

    async def _rules(self, origin: str) -> RobotFileParser:
        if origin not in self.robots:
            # Cache failures as disallow to avoid repeated robots requests.
            self.robots[origin] = None
            status, body, content_type, _ = await self._request(origin + "/robots.txt")
            if status == 404:
                body = "User-agent: *\nAllow: /"
            elif (
                status != 200
                or "html" in content_type.lower()
                or "<html" in body.lower()
            ):
                raise CrawlBlocked("Robots policy could not be verified; host skipped.")
            rules = RobotFileParser()
            rules.parse(body.splitlines())
            self.robots[origin] = rules
        cached_rules = self.robots[origin]
        if cached_rules is None:
            raise CrawlBlocked("Robots policy unavailable; host skipped.")
        return cached_rules

    async def fetch(self, url: str) -> FetchedPage:
        for _ in range(4):
            url = approved_url(url, self.hosts)
            parts = urlsplit(url)
            rules = await self._rules(f"https://{parts.netloc}")
            if not rules.can_fetch(USER_AGENT, url):
                raise CrawlBlocked("Disallowed by university robots policy.")
            rate = rules.request_rate(USER_AGENT)
            delay = max(
                float(rules.crawl_delay(USER_AGENT) or 1),
                rate.seconds / rate.requests if rate and rate.requests else 1,
            )
            status, body, content_type, location = await self._request(url, delay)
            if status in (301, 302, 303, 307, 308):
                url = approved_url(urljoin(url, location), self.hosts)
                continue
            if status != 200:
                raise CrawlBlocked(f"University returned HTTP {status}.")
            if "text/html" not in content_type.lower():
                raise CrawlBlocked("Only public HTML pages are supported in this scan.")
            return FetchedPage(url, body)
        raise CrawlBlocked("University redirect limit reached.")
