import sys
import os
import tempfile

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

scripts_dir = os.path.join(root_dir, "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from build_project_documents import (
    build_poster_pdf,
    build_review_paper_pdf,
    build_research_paper_pdf
)


def test_build_poster_pdf_generation():
    """Verify build_poster_pdf generates a valid PDF file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = os.path.join(tmpdir, "test_poster.pdf")
        build_poster_pdf(out_pdf)
        assert os.path.exists(out_pdf)
        assert os.path.getsize(out_pdf) > 1000
        with open(out_pdf, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-"


def test_build_review_paper_pdf_generation():
    """Verify build_review_paper_pdf generates a valid PDF preprint."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = os.path.join(tmpdir, "test_review.pdf")
        build_review_paper_pdf(out_pdf)
        assert os.path.exists(out_pdf)
        assert os.path.getsize(out_pdf) > 1000
        with open(out_pdf, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-"


def test_build_research_paper_pdf_generation():
    """Verify build_research_paper_pdf generates a valid PDF preprint."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = os.path.join(tmpdir, "test_research.pdf")
        build_research_paper_pdf(out_pdf)
        assert os.path.exists(out_pdf)
        assert os.path.getsize(out_pdf) > 1000
        with open(out_pdf, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-"
