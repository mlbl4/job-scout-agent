import re
from pathlib import Path

from pypdf import PdfReader


def read_cv(path: str | Path) -> str:
    """Extract text from a PDF CV and collapse extra whitespace."""
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return re.sub(r"\s+", " ", " ".join(pages)).strip()
