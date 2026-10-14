"""MCP server entry point: registers every read-only ExirYab tool."""

import logging

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from . import __version__, doctors, lookup  # noqa: F401  (imports register the tools)
from .registry import TOOLS

INSTRUCTIONS = """\
Official read-only access to ExirYab (exiryab.com, اکسیریاب), a directory of Iranian doctors: names,
specialties, clinics and offices with address, phone, working hours and map location. There is no
booking, login or payment here; give the user the doctor's profile `url` and the clinic phones.

Workflow:
1. ey_search_doctors(name, city, specialty, alternatives) with at least one of the three. Persian
   works best: name='موسی ملک محمدی', city='تهران' (or a province: 'فارس'), specialty='قلب'.
   It returns best_match plus alternatives; check `confidence` and `warnings` before trusting it.
   confidence 'medium' or 'low' means ask the user which doctor they meant (show a few alternatives).
2. Unsure of the spelling, or a word is ambiguous: ey_cities(query) and ey_specialties(query) give
   the exact Persian names with doctor counts. Then search again with that name.
3. To show where a doctor works, use the clinic `map` links (Google Maps, directions, Neshan, Balad)
   and `phones`; `weekly_hours` is per English weekday ([] = closed).

Data notes: `verified` = medical council card checked and mobile confirmed; `managed_by_doctor` =
the doctor confirmed their mobile and manages the profile; `recommendations` are patient suggestions.
Results are cached for up to a day. The API allows 60 requests per minute per IP: do not loop over
many searches. This is a directory, not medical advice.
"""

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)

mcp = MCPServer(
    "exiryab-mcp",
    title="ExirYab",
    instructions=INSTRUCTIONS,
    version=__version__,
    website_url="https://exiryab.com",
)

for fn, title in TOOLS:
    mcp.add_tool(fn, title=title, annotations=READ_ONLY)


def main() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)  # one INFO line per request floods client logs
    mcp.run()


if __name__ == "__main__":
    main()
