"""Doctor search: the best match for a name, city and specialty, plus alternatives with clinics and maps."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from .http import fetch
from .registry import tool

ALTERNATIVE_BIO_CHARS = 300  # the best match keeps its full bio (the API caps it at 1200)

# The API's warnings point at its own lookup endpoints; the agent knows them as tools.
LOOKUP_NAMES = {"/api/v1/cities": "ey_cities", "/api/v1/specialties": "ey_specialties"}


@tool("Find a doctor")
async def ey_search_doctors(
    name: Annotated[
        str | None,
        Field(
            min_length=2,
            max_length=100,
            description="Doctor's name in Persian, full or partial ('موسی ملک محمدی', 'دکتر محمدی'). Titles like «دکتر» are ignored; city or specialty words inside it ('محمدی قلب تهران') are used as filters.",
        ),
    ] = None,
    city: Annotated[
        str | None,
        Field(
            min_length=2,
            max_length=100,
            description="Persian city name ('تهران', 'شیراز') or a province name ('فارس') to search the whole province. Use ey_cities for the exact spelling.",
        ),
    ] = None,
    specialty: Annotated[
        str | None,
        Field(
            min_length=2,
            max_length=100,
            description="Persian specialty, exact or a key word: 'قلب' resolves to «قلب و عروق», 'اطفال' to «کودکان (اطفال)». Use ey_specialties to see the options.",
        ),
    ] = None,
    alternatives: Annotated[
        int, Field(ge=0, le=10, description="How many other doctors to return after the best match.")
    ] = 4,
) -> dict[str, Any]:
    """Find an Iranian doctor on exiryab.com by name, city and/or specialty: the best match plus alternatives, each with profile URL, clinics, phones, working hours and map links.

    Give at least one of name, city, specialty (Persian works best). With a name, the server ranks by
    how well the name matches and drops filters that leave no match (see `understood.dropped_filters`
    and `warnings`). Without a name, it returns the top-ranked doctors for the city and specialty.

    `confidence`: high = one clear match for the name; medium = a good match but others are close,
    so confirm with the user; low = only weak name matches; ranking = no name was given; none = nothing found.
    `match.kind` per doctor: name, partial_name, similar (padding: same specialty and area, not the
    name asked for) or ranking. Clinic `weekly_hours` maps an English day to its shifts
    ('17:00-19:00'); an empty list means closed that day.
    """
    if not any(v and v.strip() for v in (name, city, specialty)):
        raise ToolError("Give at least one of name, city or specialty.")
    body = await fetch(
        "/api/v1/doctors/search",
        {"name": name, "city": city, "specialty": specialty, "alternatives": alternatives},
    )
    q = body.get("query") or {}
    resolved_city = q.get("city") or {}
    best = body.get("bestMatch")
    return {
        "understood": {
            "name": q.get("name"),
            "city": resolved_city.get("name"),
            "province": q.get("province") or resolved_city.get("province"),
            "specialty": (q.get("specialty") or {}).get("name"),
            "dropped_filters": q.get("relaxed") or [],
        },
        "confidence": body.get("confidence"),
        "total_matches": body.get("totalMatches"),
        "best_match": doctor(best) if best else None,
        "alternatives": [doctor(d, bio_chars=ALTERNATIVE_BIO_CHARS) for d in body.get("alternatives") or []],
        "warnings": [_tool_names(w) for w in body.get("warnings") or []],
        "search_url": body.get("searchUrl"),
    }


def doctor(d: dict[str, Any], bio_chars: int | None = None) -> dict[str, Any]:
    """A compact doctor card: empty fields are dropped, map links are per clinic."""
    bio = d.get("bio")
    if bio and bio_chars and len(bio) > bio_chars:
        bio = bio[:bio_chars].rstrip() + "…"
    match = d.get("match") or {}
    return _compact(
        {
            "id": d.get("id"),
            "name": d.get("fullName"),
            "gender": d.get("gender") if d.get("gender") != "unknown" else None,
            "specialty": (d.get("specialty") or {}).get("name"),
            "medical_council_number": d.get("medicalCouncilNumber"),
            "url": d.get("profileUrl"),
            "image": d.get("photoUrl"),
            "verified": d.get("verified"),
            "managed_by_doctor": d.get("mobileVerified"),
            "featured": d.get("isFeatured"),
            "recommendations": d.get("suggestCount"),
            "profile_views": d.get("visitCount"),
            "insurances": d.get("insurances"),
            "tags": d.get("tags"),
            "website": d.get("website"),
            "instagram": d.get("instagram"),
            "online_booking_url": d.get("onlineBookingUrl"),
            "bio": bio,
            "clinics": [clinic(c) for c in d.get("clinics") or []],
            "match": _compact(
                {
                    "kind": match.get("kind"),
                    "score": match.get("score"),
                    "city_matched": match.get("cityMatched"),
                    "specialty_matched": match.get("specialtyMatched"),
                }
            ),
        }
    )


def clinic(c: dict[str, Any]) -> dict[str, Any]:
    city = c.get("city") or {}
    loc = c.get("location")
    hours = {h["day"]: [] if h.get("closed") else h.get("shifts") or [] for h in c.get("weeklyHours") or []}
    return _compact(
        {
            "type": c.get("facilityType"),
            "city": city.get("name"),
            "province": city.get("province"),
            "district": c.get("district"),
            "address": c.get("address"),
            "phones": c.get("phones"),
            "working_hours": c.get("workingHours"),
            "weekly_hours": hours,
            "map": _compact(
                {
                    "lat": loc.get("latitude"),
                    "lng": loc.get("longitude"),
                    "google_maps": loc.get("googleMapsUrl"),
                    "directions": loc.get("directionsUrl"),
                    "neshan": loc.get("neshanUrl"),
                    "balad": loc.get("baladUrl"),
                }
            )
            if loc
            else None,
        }
    )


def _compact(d: dict[str, Any]) -> dict[str, Any]:
    """Drop None, empty strings, lists and dicts; keep False and 0 (they carry meaning)."""
    return {k: v for k, v in d.items() if v is not None and v != "" and v != [] and v != {}}


def _tool_names(warning: str) -> str:
    for path, name in LOOKUP_NAMES.items():
        warning = warning.replace(path, name)
    return warning
