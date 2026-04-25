# py-amazing-marvin

Async Python client library for the Amazing Marvin API.

## Conventions

- Conventional Commits for all commit messages (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).
- Async-first: never introduce blocking I/O.
- Fully typed: dataclasses + type hints throughout. No untyped `Any` leaks across the public API.
- No global state. The client takes or manages an `aiohttp.ClientSession` explicitly.
- Suitable as a Home Assistant integration dependency.

## Project Layout

- `src/amazing_marvin/` — library code (`client.py`, `models.py`, `exceptions.py`).
- `tests/` — `pytest-asyncio` test suite with mocked HTTP.
- `specs/` — Spec Kit feature specifications.
