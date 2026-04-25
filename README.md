# amazing-marvin

[![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Async Python client library for the [Amazing Marvin](https://amazingmarvin.com) API.

Async-first, fully typed, no global state, no blocking I/O. Suitable for any Python application — CLIs, web services, MCP servers, Home Assistant integrations, sync bridges, scheduled scripts.

---

## Installation

```bash
pip install amazing-marvin
```

Requires Python 3.12+ and `aiohttp>=3.9`.

---

## Quick Start

```python
import asyncio
from amazing_marvin import MarvinClient

async def main():
    async with MarvinClient(api_token="your_token") as client:
        tasks = await client.get_today_items()
        for task in tasks:
            print(task.title, task.done)

asyncio.run(main())
```

When embedding inside a host that already manages an `aiohttp.ClientSession` (FastAPI, Home Assistant, an MCP server runtime), pass the existing session at construction so the client never owns or closes it:

```python
client = MarvinClient(
    api_token=token,
    full_access_token=full_token,   # optional
    tz_offset=600,                  # AEST
    throttle=True,
    session=existing_session,       # borrowed; not closed by client
)
tasks = await client.get_today_items()
task = await client.mark_done(item_id)
```

---

## Use Cases

The library is intentionally framework-agnostic. Common embeddings:

- **MCP servers** — wrap each `MarvinClient` method as a tool; the typed dataclasses serialise cleanly to JSON.
- **Home Assistant integrations** — use the borrowed-session pattern with `async_get_clientsession(hass)`.
- **CLIs** — pair with Typer or Click for terminal-driven task entry.
- **FastAPI / web dashboards** — share the app's `aiohttp` session via lifespan.
- **Sync bridges** — Notion, Todoist, Linear, calendar providers.
- **Scheduled scripts** — cron, GitHub Actions, weekly reviews, exports.

---

## Auth Setup

Amazing Marvin exposes two separate tokens, both found under **Profile > Integrations > API** in the Marvin app:

| Token | Constructor arg | Required for |
|---|---|---|
| API Token | `api_token` | Read and write operations (most methods) |
| Full Access Token | `full_access_token` | Raw document access, reminders, admin ops |

Methods that need a token you have not supplied will raise `MarvinAuthError` before making any HTTP request.

---

## Rate Limits

The Amazing Marvin API enforces:

- **Burst**: 1 request per 3 seconds
- **Daily cap**: 1440 requests per calendar day (resets at midnight in your local timezone)

Pass `throttle=True` to have the client enforce these limits automatically using an internal asyncio lock. When the daily cap is hit, `MarvinRateLimitError` is raised with `daily_cap_exceeded=True`. When the server itself returns 429, `MarvinRateLimitError` is raised with the `retry_after` value from the response header (if present).

---

## Timezone Handling

Marvin uses **integer minutes east of UTC** for timezone offsets. For example:

- `tz_offset=600` — AEST (UTC+10)
- `tz_offset=0` — UTC
- `tz_offset=-300` — EST (UTC-5)

Pass `tz_offset` at client construction for a default, or override it per-call on methods that accept `tz_offset=`. The offset affects which calendar day is considered "today" for scheduling and daily cap resets.

---

## Licence

MIT — see [LICENSE](LICENSE).
