"""DOCX parser using python-docx."""

from io import BytesIO

from docx import Document

from .models import ParsedSection


def parse_docx(data: bytes) -> list[ParsedSection]:
    document = Document(BytesIO(data))
    sections: list[ParsedSection] = []
    heading: str | None = None
    text_parts: list[str] = []
    order_index = 0

    def flush() -> None:
        nonlocal heading, text_parts, order_index
        text = "\n".join(part for part in text_parts if part.strip()).strip()
        if text:
            sections.append(
                ParsedSection(
                    heading=heading,
                    text=text,
                    order_index=order_index,
                )
            )
            order_index += 1
        heading = None
        text_parts = []

    for paragraph in document.paragraphs:
        style_name = (paragraph.style.name or "").lower()
        if "heading" in style_name:
            flush()
            heading = paragraph.text.strip() or None
        else:
            text_parts.append(paragraph.text)

    flush()
    return sections
