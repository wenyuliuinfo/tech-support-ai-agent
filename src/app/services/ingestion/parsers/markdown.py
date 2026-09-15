"""Markdown parser."""

import re

from .models import ParsedSection


def extract_title(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return "Untitled"


def split_by_heading(content: str) -> list[ParsedSection]:
    heading_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(content))

    if not matches:
        return [ParsedSection(heading=None, text=content, order_index=0)]

    sections: list[ParsedSection] = []
    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        sections.append(
            ParsedSection(
                heading=heading,
                text=content[start:end].strip(),
                order_index=i,
            )
        )

    first_start = matches[0].start()
    if first_start > 0:
        pre_content = content[:first_start].strip()
        if pre_content:
            sections.insert(0, ParsedSection(heading=None, text=pre_content, order_index=0))
            sections = [
                ParsedSection(
                    heading=section.heading,
                    text=section.text,
                    page_number=section.page_number,
                    order_index=section.order_index + 1,
                )
                for section in sections[1:]
            ]

    return sections


def parse_markdown(data: bytes) -> list[ParsedSection]:
    return split_by_heading(data.decode("utf-8"))
