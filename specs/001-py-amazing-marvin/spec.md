# Feature Specification: py-amazing-marvin

**Feature Branch**: `001-py-amazing-marvin`
**Created**: 2026-04-25
**Status**: Draft
**Input**: User description: "Build py-amazing-marvin — a modern async Python client library for the Amazing Marvin API. Async-first, fully typed, two auth modes, typed exceptions, rate limit awareness, timezone-aware, full API coverage (including documented experimental endpoints). Primary use case: a Home Assistant integration dependency."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read tasks from a Home Assistant integration (Priority: P1)

A Home Assistant integration developer wires the library into the integration's `async_setup_entry` to fetch the user's open tasks for today. The integration calls the library inside HA's existing event loop, passes in HA's shared `aiohttp` session, and gets back strongly typed task objects it can map onto `todo` entities. Today's date must respect the user's configured timezone offset, otherwise items roll over at the wrong moment.

**Why this priority**: This is the foundational read path. Without it, no integration use case works. It validates auth, transport, typing, timezone handling, and async session management end-to-end.

**Independent Test**: Authenticate with a real or mocked Marvin account, request today's tasks, and confirm the returned objects expose stable typed fields (`_id`, `title`, `done`, `parentId`, `day`, `db`) and that the day filter respects an explicit `tz_offset`.

**Acceptance Scenarios**:

1. **Given** a valid API token and a Marvin account with two scheduled tasks for today, **When** the integration calls the "tasks for today" method passing an externally owned `aiohttp` session, **Then** the call returns exactly those two tasks as typed objects without opening or closing the caller's session.
2. **Given** a `tz_offset` of `-300` minutes (US Eastern), **When** the local clock is 23:30 UTC on day N, **Then** "today" resolves to day N − 1 from Marvin's perspective and returns that day's tasks.
3. **Given** an invalid API token, **When** any read method is called, **Then** the call raises a typed authentication error and does not retry.

---

### User Story 2 - Mark a subtask complete in response to a sensor (Priority: P1)

A Home Assistant automation fires when a vibration sensor detects the morning meds basket has been moved. The integration uses the library to mark the corresponding Marvin subtask complete. The call must complete within a single HA service call without blocking the event loop, must surface a typed error if the subtask ID is wrong, and must not silently succeed when the API returns a non-2xx response.

**Why this priority**: This is the primary write path that drives the user's flagship use case (the morning routine). Without reliable, observable completion, sensor automations can't trust the library.

**Independent Test**: Call the "mark task done" method with a known subtask ID, assert the returned object reflects `done=true`, and confirm an unknown ID raises a typed not-found error rather than returning a misleading default.

**Acceptance Scenarios**:

1. **Given** a valid full-access token and a known open subtask ID, **When** the integration calls the mark-done method, **Then** the call returns a typed task object with `done=true` and persists the change in Marvin.
2. **Given** a method that requires the full-access token, **When** the client is configured with only the read-only API token, **Then** the call raises a typed authentication error before any HTTP request is sent.
3. **Given** a subtask ID that does not exist, **When** mark-done is called, **Then** a typed not-found error is raised carrying the offending ID.

---

### User Story 3 - Survive Marvin's rate limit without breaking the integration (Priority: P1)

The HA integration may briefly fan out several calls (e.g., one mark-done per subtask after a triggered automation) and Marvin enforces a 1-request-per-3-second burst plus 1440/day cap. The library must let the integration either opt into automatic throttling (so calls queue and complete in order) or opt out and handle 429 responses themselves. Either way, the integration must never get an opaque transport error when the limit is hit.

**Why this priority**: Without rate-limit awareness, a routine morning-flurry of completions trips Marvin's limiter and leaves the integration in an undefined state. This is a P1 because it's the dominant production failure mode for the target use case.

**Independent Test**: Configure the client with built-in throttling enabled, issue 5 calls in rapid succession against a mock that enforces the 3-second window, and confirm all 5 succeed in order with appropriate spacing. Then disable throttling, repeat, and confirm a typed rate-limit error surfaces with retry-after metadata.

**Acceptance Scenarios**:

1. **Given** built-in throttling is enabled, **When** the caller issues five back-to-back calls, **Then** they complete sequentially within Marvin's burst limit without raising rate-limit errors.
2. **Given** built-in throttling is disabled, **When** the server returns a 429, **Then** the call raises a typed rate-limit error exposing any `Retry-After` value and the daily-cap state where available.
3. **Given** the daily 1440-call budget would be exceeded, **When** the next call is attempted with throttling enabled, **Then** the library raises a typed rate-limit error rather than silently sleeping past midnight.

---

### User Story 4 - Cover the full documented API surface (Priority: P2)

A library user beyond the Home Assistant case (e.g., a CLI tool, an analytics script, a different integration) needs access to the full documented Marvin API: tasks, projects, categories, labels, habits, time tracking, calendar items, goals, rewards, and account/profile reads. Each method declares which auth mode it needs and which endpoints are flagged experimental in the upstream docs.

**Why this priority**: Coverage drives adoption and avoids forcing consumers to fork or monkey-patch when they hit a missing endpoint. Required for PyPI publication to be credible. Lower priority than P1 because the HA integration only exercises a slice of the surface.

**Independent Test**: For each documented endpoint, invoke the corresponding library method against a mocked HTTP layer and confirm the request matches the documented contract (path, headers, body shape) and the response is parsed into a typed model.

**Acceptance Scenarios**:

1. **Given** the upstream Marvin API wiki lists N documented endpoints, **When** the library is inspected, **Then** every one has a corresponding async method with a typed signature and return type.
2. **Given** an endpoint flagged experimental upstream, **When** a developer reads the method's docstring, **Then** the experimental status is stated explicitly along with any known stability caveats.
3. **Given** a method that needs the full-access token, **When** the client is constructed without one, **Then** that method raises a typed authentication error before issuing a request.

---

### User Story 5 - Publish to PyPI with a clean dependency footprint (Priority: P2)

A maintainer publishes the package to PyPI under the MIT licence. The package must install cleanly into a Home Assistant custom integration's manifest with no extras, no system dependencies, and no `requests` (HA forbids blocking I/O in integration code).

**Why this priority**: Publication is required for the HA integration to depend on the library by name in `manifest.json`. Until then, consumers must vendor the source.

**Independent Test**: Build a wheel, install it into a clean virtualenv, import the public surface, and confirm no transitive dependency pulls in `requests` or any other blocking HTTP client.

**Acceptance Scenarios**:

1. **Given** a fresh virtualenv with only Python and pip, **When** the published wheel is installed, **Then** importing the public client succeeds and the dependency tree contains `aiohttp` but not `requests`.
2. **Given** the package metadata, **When** inspected, **Then** licence is MIT, supported Python versions match Home Assistant's current minimum, and `py.typed` is present so type checkers see the annotations.

---

### Edge Cases

- **Session ownership**: caller-supplied `aiohttp` session must never be closed by the client; client-managed session must be closed exactly once on context exit.
- **Concurrent calls**: when the same client instance is used from multiple coroutines, the rate limiter must coordinate across them (no double-spend of the burst budget).
- **Clock skew vs `tz_offset`**: if a per-call `tz_offset` is passed, it must override the client-level default for that call only and not mutate client state.
- **Partial network failure**: a connection reset mid-request must surface as the typed API error, not as a raw `aiohttp` exception leaking transport details.
- **Invalid JSON from server**: an unexpected non-JSON or schema-violating response must raise the typed API error with the raw payload accessible for diagnostics.
- **Daily budget reset**: the 1440/day counter must reset on the user's local day boundary as defined by `tz_offset`, not UTC.
- **Method requires write token but only read token configured**: detected before any HTTP call, with a typed auth error naming the missing token type.

## Requirements *(mandatory)*

### Functional Requirements

**Auth & client lifecycle**

- **FR-001**: Library MUST support two authentication modes — a read-only API token (sent as `X-API-Token`) and a full-access token (sent as `X-Full-Access-Token`) — and each method MUST declare which token it requires.
- **FR-002**: Library MUST raise a typed authentication error before issuing any HTTP request when a method requires a token type that the client was not configured with.
- **FR-003**: Library MUST allow the caller to either (a) pass in an externally owned `aiohttp.ClientSession` that the client will not close, or (b) construct the client as an async context manager that owns and closes its own session on exit.
- **FR-004**: Library MUST hold no module-level mutable state. Multiple client instances with different credentials MUST coexist in the same process without interference.
- **FR-005**: Library MUST never perform blocking I/O on the event loop (no `requests`, no synchronous file or network calls in hot paths).

**Errors**

- **FR-006**: Library MUST expose a typed exception hierarchy: `MarvinAuthError`, `MarvinRateLimitError`, `MarvinNotFoundError`, `MarvinAPIError`, with `MarvinAPIError` as the common base for all client-raised errors.
- **FR-007**: `MarvinRateLimitError` MUST expose any server-supplied `Retry-After` value and an indicator of whether the daily cap or the burst limit was hit, when that information is available.
- **FR-008**: Network or transport-layer failures MUST be wrapped in `MarvinAPIError` with the original cause attached; raw `aiohttp` exceptions MUST NOT cross the public boundary.

**Rate limiting**

- **FR-009**: Library MUST be able to enforce Marvin's documented limits — 1 request per 3 seconds (burst) and 1440 requests per day — when built-in throttling is enabled by the caller.
- **FR-010**: Built-in throttling MUST be opt-in (default off, or default on with a documented flag — design choice deferred to plan), and MUST coordinate across concurrent coroutines using the same client instance.
- **FR-011**: When throttling is disabled, server-issued 429 responses MUST surface as `MarvinRateLimitError` with the response context attached; the library MUST NOT silently retry.
- **FR-012**: Daily-cap accounting MUST roll over at the user's local day boundary as defined by `tz_offset`, not UTC.

**Timezone handling**

- **FR-013**: Library MUST accept an integer `tz_offset` (minutes from UTC, matching Marvin's conventions) at client construction.
- **FR-014**: Methods that resolve a "day" or date-range argument MUST also accept a per-call `tz_offset` override that does not mutate client state.
- **FR-015**: All date/day arguments and return fields MUST be interpreted consistently against the active `tz_offset`; behaviour at midnight boundaries MUST be deterministic and documented.

**Typing & API surface**

- **FR-016**: All public methods, parameters, and return values MUST be type-annotated. The package MUST ship a `py.typed` marker so downstream type checkers (mypy, pyright) consume the annotations.
- **FR-017**: All response payloads MUST be parsed into typed dataclasses (or equivalent typed models) defined in a dedicated models module. Raw `dict[str, Any]` MUST NOT cross the public API.
- **FR-018**: Library MUST expose an async method for every endpoint documented in the upstream Amazing Marvin API wiki that is reachable with either auth mode.
- **FR-019**: Methods backing endpoints flagged experimental in the upstream docs MUST be implemented and MUST state the experimental/stability status in their docstrings.
- **FR-020**: Code MUST be structured with clean separation: HTTP/transport in a client module, typed payload models in a models module, and exceptions in an exceptions module.

**Testing & packaging**

- **FR-021**: A `pytest-asyncio` test suite MUST cover authentication, rate-limit handling, timezone resolution, error mapping, and at least one method per documented endpoint group, using mocked HTTP responses (no live network calls).
- **FR-022**: Package MUST be PyPI-publishable with a `pyproject.toml`, an MIT licence file, and metadata declaring runtime dependencies (notably `aiohttp`) and supported Python versions.
- **FR-023**: Public surface MUST be importable from a stable top-level package name without requiring private-module imports.

### Key Entities

- **Client**: Holds credentials (one or both tokens), `tz_offset`, optional rate-limiter state, and either an owned or borrowed HTTP session. Exposes one async method per documented Marvin endpoint.
- **Token type**: Enumerated as read-only API token vs full-access token; methods are tagged with the type they need so misuse is caught client-side.
- **Task**: Marvin's primary work unit. Carries `_id`, `title`, `done`, `parentId`, `day`, `db`, plus the rest of the documented fields. Supports parent-child (subtask) relationships.
- **Project / Category / Label**: Marvin's organisational hierarchy referenced by tasks.
- **Habit / Goal / Reward**: Marvin's tracking objects exposed by the documented API.
- **Time-tracking entry**: Documented session/timer objects associated with tasks.
- **Calendar item**: Documented scheduled events in Marvin.
- **Account / profile**: User metadata returned by account read endpoints.
- **Rate-limit budget**: Internal accounting of burst window state and daily count, keyed by day boundary in the user's timezone.
- **Marvin error response**: Server-returned error payload mapped into the typed exception hierarchy.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Home Assistant integration developer can fetch today's tasks and mark a subtask complete in fewer than 20 lines of integration code, using only the library's public surface.
- **SC-002**: 100% of documented Marvin API endpoints (including those flagged experimental) have a corresponding async method on the client, verified by a coverage test that compares the method list against the upstream documentation.
- **SC-003**: No method on the public surface returns a value typed as `Any` or untyped `dict`. A type checker run with strict settings reports zero errors on the public package.
- **SC-004**: With built-in throttling enabled, a burst of 10 calls completes in order with no rate-limit errors raised; with throttling disabled, the same burst surfaces a typed rate-limit error on the second call.
- **SC-005**: The published wheel installs into a clean virtualenv in under 5 seconds and pulls in `aiohttp` with no transitive dependency on `requests` or any other blocking HTTP client.
- **SC-006**: The test suite runs offline (no network access) and reaches at least 90% line coverage on the client and models modules.
- **SC-007**: Day-boundary tests confirm "today" resolves correctly for `tz_offset` values across at least UTC−12 to UTC+14 at the seconds before and after local midnight.

## Assumptions

- The upstream Amazing Marvin API wiki (https://github.com/amazingmarvin/MarvinAPI/wiki) is the authoritative source of the API surface; if endpoints disagree with the live API, the live API wins and the discrepancy is logged in the implementation plan.
- The library targets Python versions supported by Home Assistant's current stable release (assumed 3.12+ at time of writing). Older Pythons are out of scope.
- `aiohttp` is the chosen HTTP client because Home Assistant already pins it; bringing in a different async HTTP library would duplicate transport in the HA process.
- `tz_offset` is an integer number of minutes east of UTC, matching Marvin's own convention. DST handling is the caller's responsibility — the library does not interpret IANA timezone names.
- Rate-limit accounting is best-effort and per-process. Multi-process coordination (e.g., across HA workers) is out of scope; the library raises a typed error when its own counter trips.
- Webhooks (Marvin's outbound push mechanism) are out of scope for the client library; the library is request/response only. Webhook receivers are the consumer's concern.
- The library is published under the MIT licence with copyright attributed to the maintainer of this repository.
- "Documented experimental endpoints" means endpoints the upstream wiki explicitly marks experimental or beta; undocumented endpoints discovered by reverse engineering are out of scope.
- Consumers that want logging or metrics will plug them in via standard Python logging; the library does not ship its own observability stack.
