"""Catalog commands and bounded public search."""

from typing import Literal

from pydantic import Field

from app.commerce.core.constants import NAME_SIZE, MAX_PAGE_SIZE, PAGE_SIZE
from app.commerce.core.schemas import Cents, Schema, Versioned

DESCRIPTION_SIZE = 10000


class CategoryInput(Schema):
    name: str = Field(min_length=1, max_length=NAME_SIZE)
    slug: str = Field(min_length=1, max_length=NAME_SIZE, pattern=r"^[a-z0-9-]+$")
    parent_id: str | None = None


class ProductInput(Schema):
    title: str = Field(min_length=1, max_length=NAME_SIZE)
    description: str = Field(default="", max_length=DESCRIPTION_SIZE)
    category_id: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    images: list[str] = Field(default_factory=list, max_length=MAX_PAGE_SIZE)


class SkuInput(Schema):
    spu_id: str
    code: str = Field(min_length=1, max_length=NAME_SIZE)
    title: str = Field(min_length=1, max_length=NAME_SIZE)
    attributes: dict[str, str] = Field(default_factory=dict)
    sale_cents: Cents
    original_cents: Cents


class PriceInput(Versioned):
    sale_cents: Cents
    original_cents: Cents
    activity_cents: Cents | None = None


class Visibility(Versioned):
    status: Literal["draft", "active", "inactive"]


class Search(Schema):
    q: str = Field(default="", max_length=NAME_SIZE)
    category_id: str | None = None
    min_cents: Cents = 0
    max_cents: Cents | None = None
    sort: Literal["id", "price_asc", "price_desc"] = "id"
    cursor: str = ""
    limit: int = Field(default=PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
