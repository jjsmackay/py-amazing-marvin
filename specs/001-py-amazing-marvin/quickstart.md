# Quickstart: py-amazing-marvin

Minimum working examples for the two primary use cases.

## Home Assistant integration (borrowed session)

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
        # subtask ID doesn't exist
        raise
    except MarvinAuthError:
        # wrong or missing token
        raise
```

## Standalone script (owned session, context manager)

```python
import asyncio
from amazing_marvin import MarvinClient

async def main():
    async with MarvinClient(
        api_token="YOUR_API_TOKEN",
        tz_offset=-300,  # US Eastern
        throttle=True,
    ) as client:
        tasks = await client.get_today_items()
        for task in tasks:
            print(task.title, "✓" if task.done else "○")
            for sub in task.subtasks.values():
                print(f"  {sub.title}", "✓" if sub.done else "○")

asyncio.run(main())
```

## Install

```toml
# pyproject.toml (HA custom integration)
[project]
dependencies = ["py-amazing-marvin>=0.1"]
```

```bash
# Standalone
pip install py-amazing-marvin
```
