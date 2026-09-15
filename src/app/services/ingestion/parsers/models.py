"""Shared parser models."""

from pydantic import BaseModel


class ParsedSection(BaseModel):
    heading: str | None
    text: str
    page_number: int | None = None
    order_index: int = 0
