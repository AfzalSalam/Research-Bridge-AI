"""Scan first, then extract in a killable process with bounded input/output."""

import asyncio
import sys

from pydantic import ValidationError

from app.documents.contracts import MAX_PDF_BYTES, PdfExtraction
from app.documents.scanner import DocumentScanner, InfectedDocument, ScanUnavailable


async def process_pdf(content: bytes, scanner: DocumentScanner) -> PdfExtraction:
    if len(content) > MAX_PDF_BYTES:
        return PdfExtraction(status="unsupported", reason="file_too_large")
    if not content.startswith(b"%PDF-"):
        return PdfExtraction(status="unsupported", reason="invalid_pdf")
    try:
        await scanner.scan(content)
    except InfectedDocument:
        return PdfExtraction(status="rejected", reason="scan_rejected")
    except ScanUnavailable:
        return PdfExtraction(status="failed", reason="scanner_unavailable")
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "app.documents.pdf_worker",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        async with asyncio.timeout(30):
            output, _ = await process.communicate(content)
        if process.returncode != 0 or len(output) > 8 * 1024 * 1024:
            return PdfExtraction(status="failed", reason="extraction_resource_limit")
        try:
            return PdfExtraction.model_validate_json(output)
        except ValidationError:
            return PdfExtraction(status="failed", reason="invalid_extraction_result")
    except TimeoutError:
        return PdfExtraction(status="failed", reason="extraction_timeout")
    finally:
        if process.returncode is None:
            process.kill()
        await process.wait()
