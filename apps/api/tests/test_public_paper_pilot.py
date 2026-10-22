import hashlib

import pytest

from scripts.run_public_paper_pilot import load_source


def test_pdf_hash_mismatch_stops_before_parsing(tmp_path):
    path = tmp_path / "paper.pdf"
    path.write_bytes(b"not the labelled PDF")
    with pytest.raises(ValueError, match="PDF hash"):
        load_source(path, {"pdf_sha256": "0" * 64})


def test_extraction_drift_requires_label_review(tmp_path, monkeypatch):
    path = tmp_path / "paper.pdf"
    path.write_bytes(b"fixture")

    class Page:
        def extract_text(self):
            return "changed extraction"

    class Reader:
        pages = [Page()]

    monkeypatch.setattr(
        "scripts.run_public_paper_pilot.PdfReader", lambda *a, **k: Reader()
    )
    with pytest.raises(ValueError, match="page text changed"):
        load_source(
            path,
            {
                "pdf_sha256": hashlib.sha256(b"fixture").hexdigest(),
                "page_text_sha256": ["0" * 64],
            },
        )
