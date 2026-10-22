from typing import Literal

from pydantic import BaseModel, Field

MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 100


class PdfPage(BaseModel):
    number: int = Field(ge=1, le=MAX_PDF_PAGES)
    text: str = Field(max_length=20_000)


class PdfChunk(BaseModel):
    page: int = Field(ge=1, le=MAX_PDF_PAGES)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=1200)


class PdfExtraction(BaseModel):
    status: Literal["ready", "unsupported", "rejected", "failed"]
    reason: str
    pages: list[PdfPage] = Field(default_factory=list, max_length=MAX_PDF_PAGES)
    chunks: list[PdfChunk] = Field(default_factory=list, max_length=2000)
    warnings: list[str] = Field(default_factory=list, max_length=MAX_PDF_PAGES)
