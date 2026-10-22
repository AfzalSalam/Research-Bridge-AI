"""Fail-closed ClamAV streaming scan; files never need a public URL."""

import asyncio
import struct
from typing import Protocol

from app.documents.contracts import MAX_PDF_BYTES


class ScanUnavailable(Exception):
    """A clean scan could not be established; processing must not proceed."""


class InfectedDocument(Exception):
    """The antivirus rejected this file."""


class DocumentScanner(Protocol):
    async def scan(self, content: bytes) -> None: ...


class ClamAvScanner:
    def __init__(self, host: str, port: int = 3310, timeout: float = 30) -> None:
        self.host, self.port, self.timeout = host, port, timeout

    async def scan(self, content: bytes) -> None:
        if not self.host or len(content) > MAX_PDF_BYTES:
            raise ScanUnavailable("Scanner unavailable or upload exceeds the limit.")
        try:
            async with asyncio.timeout(self.timeout):
                reader, writer = await asyncio.open_connection(self.host, self.port)
                try:
                    writer.write(b"zINSTREAM" + bytes([0]))
                    for offset in range(0, len(content), 65536):
                        chunk = content[offset : offset + 65536]
                        writer.write(struct.pack("!I", len(chunk)) + chunk)
                        await writer.drain()
                    writer.write(struct.pack("!I", 0))
                    await writer.drain()
                    reply = await reader.readuntil(bytes([0]))
                    if reply == b"stream: OK" + bytes([0]):
                        return
                    if reply.endswith(b" FOUND" + bytes([0])):
                        raise InfectedDocument("The document did not pass scanning.")
                    raise ScanUnavailable("Scanner did not confirm a clean file.")
                finally:
                    writer.close()
                    await writer.wait_closed()
        except (
            OSError,
            TimeoutError,
            asyncio.IncompleteReadError,
            asyncio.LimitOverrunError,
        ) as exc:
            raise ScanUnavailable("Scanner unavailable. Try again later.") from exc
