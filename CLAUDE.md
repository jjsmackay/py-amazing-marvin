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
