# py-amazing-marvin

[![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Async Python client library for the [Amazing Marvin](https://amazingmarvin.com) API.

Built for use as a Home Assistant integration dependency: async-first, fully typed, no global state, no blocking I/O.

---

## Installation

```bash
pip install py-amazing-marvin
```

Requires Python 3.12+ and `aiohttp>=3.9`.

---

## Quick Start

The example below shows the Home Assistant borrowed-session pattern — pass an existing `aiohttp.ClientSession` at construction so the client never owns or closes it.

```python
import aiohttp
from amazing_marvin import MarvinClient, MarvinAuthError, MarvinNotFoundError

async def async_setup_entry(hass, entry):
    session = async_get_clientsession(hass)
    client = MarvinClient(
        api_token=entry.data["api_token"],
        full_access_token=entry.data.get("full_access_token"),
        tz_offset=entry.data.get("tz_offset", 0),
        throttle=True,
        session=session,
    )
    # No context manager needed — session is borrowed
    tasks = await client.get_today_items()
    return tasks

async def mark_subtask_done(client: MarvinClient, item_id: str) -> None:
    try:
        task = await client.mark_done(item_id)
        assert task.done
    except MarvinNotFoundError:
        raise
    except MarvinAuthError:
        raise
```

When you own the session yourself (scripts, tests), use the async context manager:

```python
async with MarvinClient(api_token="your_token") as client:
    tasks = await client.get_today_items()
```

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

Marvin uses **integer minutes east of UTC** for timezone offsets (matching the JavaScript `Date.getTimezoneOffset()` sign convention inverted). For example:

- `tz_offset=600` — AEST (UTC+10)
- `tz_offset=0` — UTC
- `tz_offset=-300` — EST (UTC-5)

Pass `tz_offset` at client construction for a default, or override it per-call on methods that accept `tz_offset=`. The offset affects which calendar day is considered "today" for scheduling and daily cap resets.

---

## Licence

MIT — see [LICENSE](LICENSE).
