<!-- mcp-name: io.github.sshnevis/exiryab-mcp -->

<div align="center">

# 🩺 exiryab-mcp: ExirYab MCP server for AI agents

**Official, read-only MCP server that lets your AI agent find Iranian doctors on ExirYab (اکسیریاب, exiryab.com).**<br>
Search by name, city and specialty, and get the doctor's profile link, clinics, phones, working hours<br>
and map location (Google Maps, Neshan, Balad), all from Claude, Cursor or Copilot.

[![PyPI](https://img.shields.io/pypi/v/exiryab-mcp?color=2563eb)](https://pypi.org/project/exiryab-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/exiryab-mcp)](https://pypi.org/project/exiryab-mcp/)
[![CI](https://github.com/sshnevis/exiryab-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/sshnevis/exiryab-mcp/actions/workflows/ci.yml)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-io.github.sshnevis%2Fexiryab--mcp-7c3aed)](https://registry.modelcontextprotocol.io/?q=exiryab-mcp)
[![License: MIT](https://img.shields.io/badge/license-MIT-16a34a)](https://github.com/sshnevis/exiryab-mcp/blob/main/LICENSE)

[![Install in Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=exiryab&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJleGlyeWFiLW1jcCJdfQ==)
[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_exiryab--mcp-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=exiryab&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22exiryab-mcp%22%5D%7D)

[Quick start](#quick-start) · [What it can do](#what-it-can-do) · [Tools](#tools) · [FAQ](#faq) · [فارسی](#فارسی)

</div>

---

## For AI agents

- **What:** Official MCP server for ExirYab (اکسیریاب, exiryab.com), a directory of Iranian doctors. Queries in Persian work best.
- **Install:** `claude mcp add exiryab -- uvx exiryab-mcp` (stdio, needs [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.10+).
- **Auth:** none. Optional `EXIRYAB_MCP_PROXY` sets an HTTP proxy for every request.
- **Access:** read-only. There is no booking or login; give the user the doctor's profile `url` and clinic phones.
- **Tools:** 3, all prefixed `ey_`: `ey_search_doctors`, `ey_cities`, `ey_specialties`.
- **Typical sequence:** `ey_search_doctors` -> (if a name or word is unclear) `ey_cities` / `ey_specialties` -> `ey_search_doctors` again.
- **Use when:** the user wants to find a specific doctor or the best doctors of a specialty in an Iranian city, with address, phone, hours and map.
- **Do not use when:** the user needs medical advice, or wants to book or pay online.
- **Output:** compact JSON. A `best_match` plus `alternatives`, a `confidence` (`high`, `medium`, `low`, `ranking`, `none`) and `warnings`. Clinic `weekly_hours` maps an English weekday to shifts (`[]` = closed).
- **Machine-readable:** [server.json](https://github.com/sshnevis/exiryab-mcp/blob/main/server.json), the site's [llms.txt](https://exiryab.com/llms.txt), and the catalog of Iranian MCP servers [awesome-iran-mcp](https://github.com/sepehr071/awesome-iran-mcp).

## Why

ExirYab (exiryab.com) lists doctors across Iran with their specialties, offices, hospitals and clinics.
People usually remember half a name ("Dr. Mohammadi, the cardiologist in Tehran"), and the agent has to turn
that into the right person and tell them where to go. `exiryab-mcp` calls ExirYab's public API, which does the
name matching on the server (titles, Arabic letters, spacing, partial names) and returns the best match with
alternatives:

> **You:** Find Dr. Malek Mohammadi, a cardiologist in Tehran. Where is the office?
>
> **Agent:** *calls* `ey_search_doctors(name="ملک محمدی", city="تهران", specialty="قلب")`
>
> Dr. Mousa Malek Mohammadi (cardiology, Tehran). Profile: https://exiryab.com/dr/36370-.../
> I also found other cardiologists in Tehran if you want alternatives.

## What it can do

- 🔎 **Find a doctor by name**, full or partial, with optional city and specialty, and tell you how sure the match is
- 🏆 **Top doctors** of a specialty in a city or a whole province when no name is given
- 🏥 **Clinics**: type (office, hospital, clinic), address, district, phones, working hours per weekday
- 🗺️ **Map location**: coordinates plus Google Maps, directions, Neshan and Balad links
- 🏷️ **Resolve words**: Persian city and specialty names, with doctor counts
- 🔒 **Read-only by design**: no login, no booking, no payment

## Quick start

You need [uv](https://docs.astral.sh/uv/getting-started/installation/).

<details open>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add exiryab -- uvx exiryab-mcp
```
</details>

<details>
<summary><b>Claude Desktop</b></summary>

Settings → Developer → Edit Config, then add:

```json
{
  "mcpServers": {
    "exiryab": { "command": "uvx", "args": ["exiryab-mcp"] }
  }
}
```
</details>

<details>
<summary><b>Cursor</b></summary>

Click **Install in Cursor** above, or add the Claude Desktop block to `~/.cursor/mcp.json`.
</details>

<details>
<summary><b>VS Code (Copilot agent mode)</b></summary>

Click **Install in VS Code** above, or add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "exiryab": { "type": "stdio", "command": "uvx", "args": ["exiryab-mcp"] }
  }
}
```
</details>

<details>
<summary><b>Anything else</b></summary>

It's a standard stdio MCP server: run `uvx exiryab-mcp`, or `pip install exiryab-mcp` and run `exiryab-mcp`.
</details>

Then just ask:

- "Find Dr. Mohammadi, the cardiologist in Tehran, and give me the office phone."
- "The best pediatricians in Fars province, with a map link."
- "Which heart specialties are there, and how many doctors does each have?"
- <span dir="rtl">دکتر ملک محمدی متخصص قلب در تهران را پیدا کن و آدرس مطبش را روی نشان بده.</span>

## How it works

```text
  AI agent  (Claude, Cursor, Copilot, ...)
      │
      │  MCP over stdio
      ▼
  exiryab-mcp  (runs on your machine)
      │
      │  HTTPS (JSON)
      └──────▶  exiryab.com/api/v1  (doctors/search, cities, specialties)
```

The API is public and needs no key. It is limited to 60 requests per minute per IP and answers are cached
for up to a day.

## Tools

| Tool | What it does |
|---|---|
| `ey_search_doctors` | Best match plus alternatives for a name, city (or province) and specialty, with profile URL, clinics, phones, hours and map links |
| `ey_cities` | Cities with doctors, their province and doctor count, most doctors first |
| `ey_specialties` | Specialties with doctor count and parent specialty, most doctors first |

All 3 tools are annotated `readOnlyHint: true` and return compact structured JSON.

## Good to know

- **Persian input works best.** Titles such as «دکتر» are ignored, and «ي»/«ك» and spacing differences are handled on the server.
- **City words in the name are used as filters**: `name="محمدی قلب تهران"` searches for Mohammadi among Tehran cardiologists.
- **A province works as a city**: `city="فارس"` searches the whole province.
- **Filters can be dropped**: when a name matches nobody with the given specialty or city, the server drops that filter and says so in `understood.dropped_filters` and `warnings`.
- **`confidence`**: `high` = one clear match; `medium` = a good match but others are close, so confirm with the user; `low` = weak matches only; `ranking` = no name was given; `none` = nothing found.
- **`similar` alternatives** are padding (same specialty and area), not people with the name you asked for.
- **`verified`** means the medical council card was checked and the mobile confirmed; **`managed_by_doctor`** means the doctor confirmed their mobile.

## FAQ

<details>
<summary><b>Is there an ExirYab API for AI agents?</b></summary>

Yes. ExirYab publishes a small public JSON API at `https://exiryab.com/api/v1` (search, cities, specialties), and this
MCP server wraps it for Claude, Cursor and Copilot.
</details>

<details>
<summary><b>Is it official, safe and free?</b></summary>

It is official (made by ExirYab), open source (MIT) and free. It is read-only, needs no account or API key, and runs on
your machine.
</details>

<details>
<summary><b>Can it book an appointment?</b></summary>

No. It gives the doctor's profile link and clinic phones; booking happens with the doctor or on the profile page.
</details>

<details>
<summary><b>A tool says "rate limiting requests"</b></summary>

The API allows 60 requests per minute per IP. Wait a minute and try again.
</details>

<details>
<summary><b>Claude Desktop says <code>uvx</code> is not found</b></summary>

Use the full path to `uvx` (`where uvx` on Windows, `which uvx` on macOS/Linux) as `command`.
</details>

<details>
<summary><b>How do I debug what the agent sees?</b></summary>

```bash
npx @modelcontextprotocol/inspector uvx exiryab-mcp
```
</details>

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `EXIRYAB_MCP_PROXY` | unset | HTTP proxy for every request, e.g. `http://user:pass@host:port` |
| `EXIRYAB_MCP_BASE_URL` | `https://exiryab.com` | API base URL, e.g. a local ExirYab for development |

<a id="فارسی"></a>

## فارسی: سرور MCP اکسیریاب

<div dir="rtl">

**exiryab-mcp** سرور MCP رسمی اکسیریاب است که به دستیار هوش مصنوعی شما (Claude، Cursor، Copilot و ...)
اجازه می‌دهد پزشکان ایران را با نام، شهر و تخصص پیدا کند و لینک صفحه پزشک، مطب‌ها، تلفن‌ها، ساعت کاری و
موقعیت روی نقشه (گوگل‌مپ، نشان، بلد) را بگیرد.

- فقط خواندنی است: ورود، نوبت‌دهی و پرداخت ندارد.
- نام پزشک را کامل یا ناقص بنویسید؛ «دکتر» و تفاوت «ی/ي» و فاصله‌ها در سرور حل می‌شود.
- به جای شهر می‌توانید نام استان را بدهید.
- روی سیستم خود شما اجرا می‌شود و فقط به API عمومی exiryab.com وصل می‌شود.

**نصب در Claude Code:**

</div>

```bash
claude mcp add exiryab -- uvx exiryab-mcp
```

<div dir="rtl">

بعد بپرسید: «یک متخصص اطفال خوب در شیراز با آدرس و لینک نقشه.»

</div>

## Development

```bash
git clone https://github.com/sshnevis/exiryab-mcp && cd exiryab-mcp
uv sync
uv run pytest            # offline, against recorded responses
uv run pytest -m live    # real API (EXIRYAB_MCP_LIVE_BASE_URL=http://localhost:5082 for a local ExirYab)
uv run ruff check .
```

Tools live in `src/exiryab_mcp/doctors.py` and `lookup.py`; each is a typed async function with a docstring that
tells the agent when to use it.

Releases: bump the version in `pyproject.toml` and `server.json`, then push a `v*` tag. GitHub Actions tests,
publishes to PyPI and the [MCP Registry](https://registry.modelcontextprotocol.io), and creates the GitHub Release.

## Related servers

- [Paziresh24 MCP server](https://github.com/sepehr071/paziresh24-mcp) and [Doctoreto MCP server](https://github.com/sepehr071/doctoreto-mcp) for appointment times and visit fees
- All Iranian MCP servers: [awesome-iran-mcp](https://github.com/sepehr071/awesome-iran-mcp)

## Disclaimer

The directory is for finding doctors and is not medical advice. Please keep request rates reasonable.

## License

[MIT](https://github.com/sshnevis/exiryab-mcp/blob/main/LICENSE)
