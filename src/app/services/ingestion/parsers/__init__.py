"""Format-specific parsers for ingestion."""

from importlib import import_module

from .markdown import extract_title, parse_markdown, split_by_heading
from .models import ParsedSection

__all__ = [
    "ParsedSection",
    "extract_title",
    "parse_docx",
    "parse_markdown",
    "parse_pdf",
    "split_by_heading",
]


def __getattr__(name: str):
    if name == "parse_pdf":
        return import_module(".pdf", __name__).parse_pdf
    if name == "parse_docx":
        return import_module(".docx", __name__).parse_docx
    raise AttributeError(name)
