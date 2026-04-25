<!--
SYNC IMPACT REPORT — 2026-04-25
================================
Version change: (unfilled template) → 1.0.0
Bump rationale: Initial ratification. Prior file was the unfilled scaffold
  template with placeholder tokens; this is the first concrete adoption.
Modified principles: N/A (initial)
Added sections:
  - Core Principles I–V (Async-First; Single-Owner State; Strict Type Safety;
    Offline Test Discipline; Publishable Library)
  - Engineering Constraints (technology pins, licensing, layout)
  - Development Workflow (Spec Kit, Conventional Commits, quality gates)
  - Governance
Removed sections: None.
Templates requiring updates:
  - ✅ .specify/templates/constitution-template.md — unchanged (this file
        is the project's instance, not the template)
  - ✅ .specify/templates/plan-template.md — Constitution Check section
        reads "Gates determined based on constitution file"; the
        feature-specific plan.md already enumerates 5 gates that map
        1:1 to the principles below, so no template change is required.
  - ✅ .specify/templates/spec-template.md — no constitution-driven section
        added or removed.
  - ✅ .specify/templates/tasks-template.md — no principle-driven task type
        added or removed.
  - ⚠ py-amazing-marvin/specs/001-py-amazing-marvin/plan.md — already
        encodes the 5 gates derived from spec; recommend a follow-up edit
        that names the constitution principles (I–V) alongside each gate
        for traceability. Non-blocking.
Follow-up TODOs: None deferred.
-->

# py-amazing-marvin Constitution

## Core Principles

### I. Async-First

The library MUST NOT introduce blocking I/O on the asyncio event loop. The HTTP
transport MUST be `aiohttp`; the `requests` library, `urllib`, synchronous
file I/O, and synchronous DNS calls MUST NOT appear in any code path reachable
from a public method.

**Rationale**: The primary consumer is Home Assistant, which forbids blocking
I/O in integration code. A single blocking call inside the event loop stalls
every coroutine in the host process. This principle protects every consumer,
not only HA, by guaranteeing the library is safe to call from any asyncio
context.

### II. Single-Owner State

All mutable state MUST live on a `MarvinClient` instance: credentials, rate
limiter counters, and the `aiohttp.ClientSession` (when client-owned). The
library MUST hold no module-level mutable state. Multiple `MarvinClient`
instances with different credentials MUST coexist in one process without
cross-instance interference. Sessions are either borrowed (caller-owned, never
closed by the client) or owned (created in `__aenter__`, closed in
`__aexit__`)—never both.

**Rationale**: Module-level state breaks multi-tenant deployments, makes
testing flaky, and produces double-close bugs around third-party sessions.
Strict single-owner state keeps the library reentrant and safe to embed.

### III. Strict Type Safety

The package MUST ship a `py.typed` marker. All public methods, parameters, and
return values MUST be type-annotated. `mypy --strict` MUST report zero errors
on the `src/amazing_marvin/` tree. Untyped `dict[str, Any]` MUST NOT cross the
public API boundary; responses are parsed into typed dataclasses with
`from_dict` classmethods that silently discard unknown fields for forward
compatibility. The single justified exception is `MarvinDocument.data`, where
the upstream CouchDB schema is intentionally dynamic.

**Rationale**: Downstream type-checkers (mypy, pyright) only consume
annotations when `py.typed` is present. Strict typing catches integration
bugs at the consumer's CI stage rather than at runtime in production HA
installs.

### IV. Offline Test Discipline

The full test suite MUST run with no network access. All HTTP MUST be mocked
through `aioresponses`. Live API calls in CI are forbidden. Test coverage on
`client.py` and `models.py` MUST be ≥ 90% line coverage. The `pytest-asyncio`
suite MUST cover authentication, rate-limit handling, timezone resolution,
error mapping, and at least one method per documented endpoint group.

**Rationale**: Network-dependent tests are flaky, leak credentials, and
exhaust the upstream 1440-call daily budget. Offline tests are the only way
to maintain a fast, deterministic CI signal that protects every release.

### V. Publishable Library

The package MUST be installable from PyPI as a wheel under the MIT licence.
The dependency tree MUST contain `aiohttp` and MUST NOT contain `requests` or
any other blocking HTTP client. Metadata MUST declare supported Python
versions matching Home Assistant's current minimum (currently 3.12+). The
top-level import name MUST remain `amazing_marvin` (distribution name
`py-amazing-marvin`); private modules (prefixed `_`) MUST NOT be required for
typical use.

**Rationale**: Home Assistant custom integrations declare dependencies by
name in `manifest.json`. Without a clean PyPI release, every consumer must
vendor source. A clean dependency tree also keeps install times short
(< 5 s into a fresh virtualenv) and avoids transitive blocking-I/O leaks.

## Engineering Constraints

- **Language/runtime**: Python 3.12+. Older Pythons are out of scope.
- **HTTP client**: `aiohttp >= 3.9`. No alternative transport is permitted.
- **Layout**: PEP 517/518 `src/` layout under `src/amazing_marvin/`. Files:
  `client.py`, `models.py`, `exceptions.py`, internal `_throttle.py`.
- **Client structure**: `MarvinClient` is a single flat class. Resource
  sub-clients (`client.tasks.add(...)`) MUST NOT be introduced.
- **Exception hierarchy**: `MarvinAPIError` is the public base. Concrete
  subclasses are `MarvinAuthError`, `MarvinRateLimitError`,
  `MarvinNotFoundError`. Raw `aiohttp` exceptions MUST NOT cross the public
  boundary.
- **Retries**: There MUST be no automatic retry. Transient failures
  (timeouts, connection resets, 5xx) are wrapped in `MarvinAPIError` and
  raised immediately; the caller decides whether to retry.
- **Timezone handling**: `tz_offset` is an integer number of minutes east of
  UTC. DST resolution is the caller's responsibility; the library does not
  interpret IANA timezone names.
- **Licence**: MIT, copyright held by the repository maintainer.

## Development Workflow

- **Spec Kit pipeline**: Features follow `/speckit-specify` → `/speckit-clarify`
  → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`.
  Skipping `/speckit-analyze` before implementation is permitted only for
  trivial doc-only changes.
- **Commits**: All commits MUST follow Conventional Commits
  (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`, `ci:`, `build:`).
- **Quality gates** (each MUST pass before merge):
  1. `pytest -q` — full suite green, offline.
  2. `pytest --cov=amazing_marvin` — ≥ 90% coverage on `client.py` and
     `models.py`.
  3. `mypy --strict src/` — zero errors.
  4. `ruff check src/ tests/` — zero errors.
  5. `pip wheel . && pip install --dry-run` — clean install, no `requests`
     in resolved dependencies.
- **Documentation**: Every public method MUST have a docstring stating its
  HTTP path, required auth token, and (where applicable) experimental
  status. Methods backing endpoints flagged experimental upstream MUST
  contain the substring "Experimental" in their docstring; this is verified
  by an automated test.

## Governance

This constitution supersedes ad-hoc conventions when they conflict. Spec,
plan, and task documents MUST be checked against these principles during
`/speckit-analyze`; any conflict is automatically a CRITICAL finding and
blocks `/speckit-implement` until either the artifact is corrected or the
constitution is amended.

**Amendments** are made through `/speckit-constitution`, which MUST:
1. Update the version per semantic versioning (MAJOR for backward-incompatible
   principle removal/redefinition; MINOR for added or materially expanded
   principles; PATCH for clarifications).
2. Update `Last Amended` to the change date.
3. Emit a Sync Impact Report as an HTML comment at the top of this file.
4. Propagate changes to dependent templates and feature plans where the
   principle is referenced.

**Version**: 1.0.0 | **Ratified**: 2026-04-25 | **Last Amended**: 2026-04-25
