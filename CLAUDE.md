# py-amazing-marvin

Async Python client library for the Amazing Marvin API.

Generic embedding target — works in any async Python host (CLIs, FastAPI, MCP servers, Home Assistant integrations, sync bridges, scheduled scripts). Public entry point: `from amazing_marvin import MarvinClient`.

## Commands

```bash
# Setup (uv-based)
uv venv .venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev]"

# Tests + coverage (must stay ≥90% on client.py and models.py)
pytest -q
pytest --cov=amazing_marvin --cov-report=term-missing

# Type and lint gates (must exit 0 before commit)
mypy --strict src/amazing_marvin/
ruff check src/ tests/
```

## Conventions

- Conventional Commits for all commit messages (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).
- Async-first: never introduce blocking I/O.
- Fully typed: dataclasses + type hints throughout. No untyped `Any` leaks across the public API.
- No global state. The client takes or manages an `aiohttp.ClientSession` explicitly.
- Framework-agnostic. The borrowed-session pattern (`session=existing`) is the contract for embedding inside hosts that own their own `aiohttp.ClientSession`.

## Project Layout

- `src/amazing_marvin/` — library code (`client.py`, `models.py`, `exceptions.py`, `_throttle.py`).
- `tests/` — `pytest-asyncio` test suite with mocked HTTP.
- `specs/` — Spec Kit feature specifications (history; not runtime).

## Gotchas

- **`tz_offset` is integer minutes east of UTC** (positive east, negative west). E.g. AEST = `600`, EST = `-300`. Sign matches Marvin's convention, opposite of `Date.getTimezoneOffset()`.
- **Two auth modes** — `api_token` (read+most write) and `full_access_token` (raw doc access, reminders, admin). Methods raise `MarvinAuthError` *before* any HTTP call if the required token isn't configured.
- **Throttle is opt-in** (`throttle=True`). Burst is 1 req/3s; daily cap is 1440 with rollover at midnight in the active timezone. Server 429s surface as `MarvinRateLimitError` with `retry_after` regardless of throttle setting.
- **Models auto-map camelCase→snake_case** via `_camel_to_snake` + `_from_dict`. Don't manually rename fields when adding to a dataclass — just declare the snake_case attribute.
- **`_from_dict` silently discards unknown keys** for forward compatibility with new Marvin API fields.
- **`_build_body(**kw)` filters None values only.** To omit a boolean when False (e.g. `done=False` shouldn't go in the body), pass `done=done or None`.
- **No automatic retries** — every transient error (5xx, network) raises immediately. Callers handle retry policy.

<!-- SPECKIT START -->
## Active Feature

**Branch**: `001-py-amazing-marvin`
**Plan**: [specs/001-py-amazing-marvin/plan.md](specs/001-py-amazing-marvin/plan.md)
**Spec**: [specs/001-py-amazing-marvin/spec.md](specs/001-py-amazing-marvin/spec.md)
**Research**: [specs/001-py-amazing-marvin/research.md](specs/001-py-amazing-marvin/research.md)
**Data model**: [specs/001-py-amazing-marvin/data-model.md](specs/001-py-amazing-marvin/data-model.md)
**Contracts**: [specs/001-py-amazing-marvin/contracts/](specs/001-py-amazing-marvin/contracts/)
**Quickstart**: [specs/001-py-amazing-marvin/quickstart.md](specs/001-py-amazing-marvin/quickstart.md)
<!-- SPECKIT END -->
