import httpx
import pytest
from conftest import fixture

pytestmark = pytest.mark.anyio

SEARCH = "/api/v1/doctors/search"


async def search(client, **args) -> dict:
    result = await client.call_tool("ey_search_doctors", args)
    assert not result.is_error, result.content[0].text
    return result.structured_content


async def test_name_search_sends_every_filter_and_returns_compact_cards(client, api):
    api[SEARCH] = fixture("search_name.json")
    data = await search(client, name="دکتر موسی ملک محمدی", city="تهران", specialty="قلب", alternatives=2)

    params = dict(api.calls[0].url.params)
    assert params == {"name": "دکتر موسی ملک محمدی", "city": "تهران", "specialty": "قلب", "alternatives": "2"}
    assert data["understood"] == {
        "name": "موسی ملک محمدی",
        "city": "تهران",
        "province": "تهران",
        "specialty": "قلب و عروق",
        "dropped_filters": [],
    }
    assert data["confidence"] == "high" and data["total_matches"] == 1
    best = data["best_match"]
    assert best["id"] == 36370 and best["name"] == "دکتر موسی ملک محمدی"
    assert best["url"].startswith("https://exiryab.com/dr/36370-")
    assert best["match"]["kind"] == "name"
    assert "fullName" not in best and "image" not in best  # camelCase gone, empty fields dropped
    assert best["verified"] is False  # False is kept: it means "not verified", not "unknown"
    assert [a["match"]["kind"] for a in data["alternatives"]] == ["similar", "similar"]
    assert data["search_url"].startswith("https://exiryab.com/search?")


async def test_clinic_has_weekly_hours_map_links_and_phones(client, api):
    api[SEARCH] = fixture("search_full.json")
    best = (await search(client, name="سینا شیری همدانی", alternatives=0))["best_match"]

    assert best["insurances"] == ["بیمه سلامت", "بیمه تامین اجتماعی", "بیمه نیروی مسلح"]
    (clinic,) = best["clinics"]
    assert clinic["type"] == "hospital" and clinic["city"] == "قزوین" and clinic["phones"] == ["02833334807"]
    assert clinic["weekly_hours"]["saturday"] == ["17:00-19:00"]
    assert clinic["weekly_hours"]["sunday"] == []
    assert clinic["working_hours"] == "شنبه و دوشنبه 17-19"
    assert clinic["map"]["lat"] == 36.275453
    assert clinic["map"]["neshan"].startswith("https://neshan.org/maps/@36.275453,50.024775")
    assert set(clinic["map"]) == {"lat", "lng", "google_maps", "directions", "neshan", "balad"}


async def test_province_search_and_clinic_without_location(client, api):
    api[SEARCH] = fixture("search_province.json")
    data = await search(client, city="فارس", specialty="اطفال", alternatives=1)

    assert data["understood"]["province"] == "فارس" and data["understood"]["city"] is None
    assert data["confidence"] == "ranking"
    clinics = data["alternatives"][0]["clinics"]
    assert "map" in clinics[0] and "map" not in clinics[1]


async def test_dropped_filter_is_reported(client, api):
    api[SEARCH] = fixture("search_relaxed.json")
    data = await search(client, name="دکتر موسی ملک محمدی", specialty="پوست", alternatives=1)

    assert data["understood"]["dropped_filters"] == ["specialty"]
    assert data["best_match"]["match"]["specialty_matched"] is False
    assert any("specialty filter was dropped" in w for w in data["warnings"])


async def test_warnings_name_the_lookup_tools(client, api):
    body = fixture("search_province.json")
    body["warnings"] = [
        "City 'xx' was not recognized, so all cities were searched. Use /api/v1/cities to find the exact Persian name.",
        "Specialty 'yy' was not recognized. Use /api/v1/specialties to find the exact Persian name.",
    ]
    api[SEARCH] = body
    warnings = (await search(client, city="xx", specialty="yy"))["warnings"]
    assert "Use ey_cities" in warnings[0] and "Use ey_specialties" in warnings[1]


async def test_alternative_bios_are_shortened_but_the_best_match_keeps_its_bio(client, api):
    body = fixture("search_name.json")
    body["bestMatch"]["bio"] = "ب" * 1000
    body["alternatives"][0]["bio"] = "الف" * 400
    api[SEARCH] = body
    data = await search(client, name="موسی ملک محمدی")
    assert len(data["best_match"]["bio"]) == 1000
    assert len(data["alternatives"][0]["bio"]) == 301 and data["alternatives"][0]["bio"].endswith("…")


async def test_no_match(client, api):
    api[SEARCH] = fixture("search_none.json")
    data = await search(client, name="زززززز", alternatives=0)
    assert data["confidence"] == "none" and data["best_match"] is None and data["alternatives"] == []


async def test_needs_name_city_or_specialty(client, api):
    result = await client.call_tool("ey_search_doctors", {"name": None, "alternatives": 2})
    assert result.is_error and "at least one" in result.content[0].text
    assert api.calls == []


async def test_alternatives_are_capped(client, api):
    result = await client.call_tool("ey_search_doctors", {"city": "تهران", "alternatives": 11})
    assert result.is_error and api.calls == []


async def test_rate_limit_message_is_passed_on(client, api):
    message = "Too many requests: the limit is 60 per minute per IP. Retry after 60 seconds."
    api[SEARCH] = lambda r: httpx.Response(429, json={"error": message}, headers={"Retry-After": "60"})
    result = await client.call_tool("ey_search_doctors", {"city": "تهران"})
    assert result.is_error and "HTTP 429" in result.content[0].text and "60 per minute" in result.content[0].text
    assert len(api.calls) == 1  # 429 is not retried


async def test_blank_filters_are_refused_before_calling_the_api(client, api):
    result = await client.call_tool("ey_search_doctors", {"city": "   "})
    assert result.is_error and api.calls == []


async def test_bad_request_shows_the_api_error(client, api):
    api[SEARCH] = (400, {"error": "Provide at least one of: name, city, specialty."})
    result = await client.call_tool("ey_search_doctors", {"name": "--"})
    assert result.is_error and "HTTP 400" in result.content[0].text and "Provide at least one" in result.content[0].text


async def test_weekly_hours_without_a_day_are_skipped(client, api):
    body = fixture("search_full.json")
    body["bestMatch"]["clinics"][0]["weeklyHours"] = [
        {"shifts": ["09:00-11:00"]},  # no "day": unusable, not an error
        {"day": "friday", "closed": True, "shifts": []},
    ]
    api[SEARCH] = body
    best = (await search(client, name="سینا شیری همدانی", alternatives=0))["best_match"]
    assert best["clinics"][0]["weekly_hours"] == {"friday": []}


async def test_non_object_body_is_a_clear_error_not_a_crash(client, api):
    api[SEARCH] = ["not", "an", "object"]
    result = await client.call_tool("ey_search_doctors", {"city": "تهران"})
    assert result.is_error and "unexpected response" in result.content[0].text
