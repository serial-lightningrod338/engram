"""Text and file source parser."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedSource:
    """A parsed source ready for ingestion."""

    content: str
    source_type: str  # "text", "url", "file", "pdf"
    origin: str  # URL, file path, or "stdin"
    title: str = ""

    @property
    def slug_hint(self) -> str:
        """Generate a slug hint from the title or origin."""
        text = self.title or self.origin
        # Clean up for slug
        slug = text.lower().strip()
        slug = "".join(c if c.isalnum() or c in (" ", "-") else "" for c in slug)
        slug = "-".join(slug.split())
        return slug[:60] or "untitled"


def parse_text(text: str, origin: str = "direct-input") -> ParsedSource:
    """Parse raw text input."""
    # Try to extract a title from the first line
    lines = text.strip().splitlines()
    title = ""
    if lines and lines[0].startswith("# "):
        title = lines[0].lstrip("# ").strip()

    return ParsedSource(
        content=text,
        source_type="text",
        origin=origin,
        title=title,
    )


def parse_file(path: Path) -> ParsedSource:
    """Parse a local file."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _parse_pdf(path)

    # Default: read as text
    content = path.read_text(errors="replace")
    return ParsedSource(
        content=content,
        source_type="file",
        origin=str(path),
        title=path.stem.replace("-", " ").replace("_", " ").title(),
    )


def _parse_pdf(path: Path) -> ParsedSource:
    """Parse a PDF file to text."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError(
            "The 'pypdf' package is required for PDF support. "
            "Install it with: pip install pypdf"
        )

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)

    content = "\n\n---\n\n".join(pages)
    return ParsedSource(
        content=content,
        source_type="pdf",
        origin=str(path),
        title=path.stem.replace("-", " ").replace("_", " ").title(),
    )
