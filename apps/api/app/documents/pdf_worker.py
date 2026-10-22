"""Isolated parser entry point. Never invoke on bytes before antivirus approval."""

import io
import sys
from collections.abc import Mapping

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from pypdf.generic import IndirectObject, NameObject

from app.documents.contracts import (
    MAX_PDF_BYTES,
    MAX_PDF_PAGES,
    PdfChunk,
    PdfExtraction,
    PdfPage,
)


class UnsupportedPdf(Exception):
    pass


def validate_structure(reader: PdfReader) -> None:
    forbidden = {
        "/JavaScript",
        "/JS",
        "/Launch",
        "/EmbeddedFiles",
        "/XFA",
        "/RichMedia",
        "/OpenAction",
        "/AA",
    }
    stack: list[object] = [reader.trailer]
    seen: set[int] = set()
    visited = 0
    while stack:
        node = stack.pop()
        if isinstance(node, IndirectObject):
            node = node.get_object()
        identity = id(node)
        if identity in seen:
            continue
        seen.add(identity)
        visited += 1
        if visited > 100_000:
            raise UnsupportedPdf("pdf_too_complex")
        if isinstance(node, NameObject) and str(node) in {
            "/JavaScript",
            "/Launch",
            "/EmbeddedFile",
            "/FileAttachment",
            "/RichMedia",
            "/SubmitForm",
            "/ImportData",
        }:
            raise UnsupportedPdf("active_or_embedded_content")
        if isinstance(node, Mapping):
            if forbidden.intersection(node):
                raise UnsupportedPdf("active_or_embedded_content")
            stack.extend(node.values())
        elif isinstance(node, (list, tuple)):
            stack.extend(node)


def extract_pdf(content: bytes) -> PdfExtraction:
    if len(content) > MAX_PDF_BYTES:
        return PdfExtraction(status="unsupported", reason="file_too_large")
    if not content.startswith(b"%PDF-"):
        return PdfExtraction(status="unsupported", reason="invalid_pdf")
    try:
        reader = PdfReader(io.BytesIO(content), strict=True)
        if reader.is_encrypted:
            return PdfExtraction(status="unsupported", reason="encrypted_pdf")
        if not 1 <= len(reader.pages) <= MAX_PDF_PAGES:
            return PdfExtraction(status="unsupported", reason="page_limit")
        validate_structure(reader)
        pages: list[PdfPage] = []
        chunks: list[PdfChunk] = []
        warnings: list[str] = []
        total_chars = 0
        for number, page in enumerate(reader.pages, 1):
            text = (page.extract_text() or "").replace(chr(0), "").strip()
            total_chars += len(text)
            if len(text) > 20_000 or total_chars > 500_000:
                raise UnsupportedPdf("extracted_text_limit")
            pages.append(PdfPage(number=number, text=text))
            if not text:
                warnings.append(
                    f"Page {number} has no extractable text; no OCR was used."
                )
            for start in range(0, len(text), 1050):
                end = min(start + 1200, len(text))
                chunk = text[start:end]
                if chunk.strip():
                    chunks.append(
                        PdfChunk(page=number, start=start, end=end, text=chunk)
                    )
                if end == len(text):
                    break
        if sum(sum(c.isalpha() for c in p.text) for p in pages) < 40:
            return PdfExtraction(status="unsupported", reason="no_extractable_text")
        return PdfExtraction(
            status="ready",
            reason="text_extracted",
            pages=pages,
            chunks=chunks,
            warnings=warnings,
        )
    except UnsupportedPdf as exc:
        return PdfExtraction(status="unsupported", reason=str(exc))
    except (PdfReadError, ValueError, TypeError, KeyError, RecursionError):
        return PdfExtraction(status="unsupported", reason="invalid_pdf")


def main() -> None:
    if sys.platform != "win32":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    content = sys.stdin.buffer.read(MAX_PDF_BYTES + 1)
    result = extract_pdf(content)
    sys.stdout.write(result.model_dump_json())


if __name__ == "__main__":
    main()
