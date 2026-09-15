"""PDF parser using pypdf."""

from io import BytesIO

from pypdf import PdfReader

from .models import ParsedSection


def parse_pdf(data: bytes) -> list[ParsedSection]:
    reader = PdfReader(BytesIO(data))
    sections: list[ParsedSection] = []
    order_index = 0

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            sections.append(
                ParsedSection(
                    heading=None,
                    text=text,
                    page_number=page_number,
                    order_index=order_index,
                )
            )
            order_index += 1

    return sections
