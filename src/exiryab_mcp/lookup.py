"""Cities and specialties as exiryab.com spells them, with doctor counts."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from .http import as_object, fetch
from .registry import tool

Query = Annotated[
    str | None,
    Field(
        min_length=1,
        max_length=100,
        description="Part of the Persian name, e.g. 'شیر' or 'قلب'. Omit to list the largest.",
    ),
]


@tool("List cities")
async def ey_cities(
    query: Query = None,
    limit: Annotated[int, Field(ge=1, le=500, description="Max cities to return.")] = 20,
) -> dict[str, Any]:
    """Cities that have doctors on exiryab.com, with their province and doctor count, most doctors first.

    Use it to find the exact Persian city name for ey_search_doctors(city=...), or to check whether
    a town is covered. `total` counts every match, not only the ones returned.
    """
    body = as_object(await fetch("/api/v1/cities", {"q": query, "limit": limit}))
    return {
        "total": body.get("total"),
        "cities": [
            {"name": c.get("name"), "province": c.get("province"), "doctors": c.get("doctorCount"), "url": c.get("url")}
            for c in body.get("items") or []
        ],
    }


@tool("List specialties")
async def ey_specialties(
    query: Query = None,
    limit: Annotated[int, Field(ge=1, le=500, description="Max specialties to return.")] = 50,
) -> dict[str, Any]:
    """Medical specialties on exiryab.com with their doctor count, most doctors first; sub-specialties name their `parent`.

    Use it to turn a word like 'قلب' or 'پوست' into the exact specialty for ey_search_doctors(specialty=...)
    when the user's word is ambiguous (heart: «قلب و عروق» cardiology or «جراح قلب» heart surgery).
    """
    body = as_object(await fetch("/api/v1/specialties", {"q": query, "limit": limit}))
    return {
        "total": body.get("total"),
        "specialties": [
            {"name": s.get("name"), "parent": s.get("parent"), "doctors": s.get("doctorCount"), "url": s.get("url")}
            for s in body.get("items") or []
        ],
    }
