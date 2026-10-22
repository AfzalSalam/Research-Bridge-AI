import asyncio
import io
import struct
from unittest.mock import AsyncMock, Mock

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    TextStringObject,
)

from app.documents.contracts import MAX_PDF_BYTES
from app.documents.pdf_worker import extract_pdf
from app.documents.processing import process_pdf
from app.documents.scanner import ClamAvScanner, InfectedDocument, ScanUnavailable


def pdf_bytes(
    texts: list[str], *, encrypted: bool = False, active: bool = False
) -> bytes:
    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(width=600, height=800)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): writer._add_object(font)}
                )
            }
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("fixture-password")
    if active:
        writer._root_object[NameObject("/OpenAction")] = DictionaryObject(
            {
                NameObject("/S"): NameObject("/JavaScript"),
                NameObject("/JS"): TextStringObject("app.alert('fixture')"),
            }
        )
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_page_numbers_and_chunk_offsets_are_source_exact():
    content = pdf_bytes(
        [
            "Research method and evaluation evidence. " * 45,
            "Limitations include the small sample size and single institution.",
        ]
    )
    result = extract_pdf(content)
    assert result.status == "ready"
    assert [page.number for page in result.pages] == [1, 2]
    assert len(result.chunks) > 2
    for chunk in result.chunks:
        assert result.pages[chunk.page - 1].text[chunk.start : chunk.end] == chunk.text
        assert len(chunk.text) <= 1200


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (b"not a PDF", "invalid_pdf"),
        (b"%PDF-corrupt", "invalid_pdf"),
        (b"%PDF-" + b"x" * MAX_PDF_BYTES, "file_too_large"),
        (pdf_bytes([""]), "no_extractable_text"),
        (pdf_bytes([""] * 101), "page_limit"),
        (pdf_bytes(["private text"], encrypted=True), "encrypted_pdf"),
        (pdf_bytes(["research text"], active=True), "active_or_embedded_content"),
    ],
    ids=[
        "not-pdf",
        "corrupt",
        "oversized",
        "scanned",
        "page-limit",
        "encrypted",
        "active",
    ],
)
def test_unsupported_documents(content, reason):
    result = extract_pdf(content)
    assert result.status == "unsupported"
    assert result.reason == reason
    assert not result.pages and not result.chunks


def test_scan_failure_never_starts_parser(monkeypatch):
    launch = AsyncMock()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
    for error, expected in [
        (ScanUnavailable(), "failed"),
        (InfectedDocument(), "rejected"),
    ]:
        scanner = AsyncMock()
        scanner.scan.side_effect = error
        result = asyncio.run(process_pdf(b"%PDF-test", scanner))
        assert result.status == expected
    launch.assert_not_called()


def test_successful_scan_then_isolated_extraction():
    scanner = AsyncMock()
    result = asyncio.run(
        process_pdf(
            pdf_bytes(
                ["The study investigates research using controlled experiments."]
            ),
            scanner,
        )
    )
    assert result.status == "ready"
    scanner.scan.assert_awaited_once()
    assert result.chunks[0].page == 1


@pytest.mark.parametrize(
    "reply,exception",
    [
        (b"stream: OK" + bytes([0]), None),
        (b"stream: Eicar FOUND" + bytes([0]), InfectedDocument),
        (b"stream: size limit ERROR" + bytes([0]), ScanUnavailable),
    ],
)
def test_clamav_protocol_and_fail_closed_reply(reply, exception):
    async def run():
        received = bytearray()

        async def handle(reader, writer):
            assert await reader.readuntil(bytes([0])) == b"zINSTREAM" + bytes([0])
            while True:
                size = struct.unpack("!I", await reader.readexactly(4))[0]
                if not size:
                    break
                received.extend(await reader.readexactly(size))
            writer.write(reply)
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        async with server:
            scanner = ClamAvScanner("127.0.0.1", server.sockets[0].getsockname()[1])
            if exception:
                with pytest.raises(exception):
                    await scanner.scan(b"test document")
            else:
                await scanner.scan(b"test document")
            assert received == b"test document"

    asyncio.run(run())


@pytest.mark.parametrize("failure", [TimeoutError, asyncio.CancelledError])
def test_parser_is_killed_on_timeout_or_cancellation(monkeypatch, failure):
    process = Mock(returncode=None)
    process.communicate = AsyncMock(side_effect=failure)
    process.wait = AsyncMock()
    monkeypatch.setattr(
        asyncio, "create_subprocess_exec", AsyncMock(return_value=process)
    )
    scanner = AsyncMock()
    if failure is asyncio.CancelledError:
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(process_pdf(b"%PDF-test", scanner))
    else:
        result = asyncio.run(process_pdf(b"%PDF-test", scanner))
        assert result.reason == "extraction_timeout"
    process.kill.assert_called_once()
    process.wait.assert_awaited_once()
