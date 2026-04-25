# Implementation Plan: py-amazing-marvin

**Branch**: `001-py-amazing-marvin` | **Date**: 2026-04-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-py-amazing-marvin/spec.md`

## Summary

Build `py-amazing-marvin` — a fully-typed, async-first Python client library for the Amazing Marvin API (`https://serv.amazingmarvin.com/api`). The library wraps 33 documented endpoints across 10 endpoint groups (test, tasks, projects, calendar, time tracking, reading, document-level, rewards, goals, habits, reminders, account). It supports two auth modes (read-only API token, full-access token), a flat client class, optional built-in rate throttling (1 req/3 s burst, 1440/day cap), integer `tz_offset` timezone handling, typed dataclass models with silent unknown-field discard, and a typed exception hierarchy. Primary delivery vehicle: a PyPI-publishable wheel that Home Assistant custom integrations can declare as a dependency with no blocking I/O and no global state.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: `aiohttp>=3.9` (HTTP transport, already pinned by HA), `pytest-asyncio` (test suite), `aioresponses` (HTTP mock in tests)
**Storage**: N/A — library, no persistent state
**Testing**: `pytest` + `pytest-asyncio` (asyncio_mode = "auto") + `aioresponses` for mocked HTTP; no live network in CI
**Target Platform**: Any Python 3.12+ environment; primary consumer is Home Assistant (Linux, any architecture)
**Project Type**: Python library (PyPI package, `src/` layout)
**Performance Goals**: Library overhead per call <5 ms (thin wrapper — transport latency dominates); throttler sleep precision within 50 ms of target window
**Constraints**: No blocking I/O on event loop; no module-level mutable state; session borrowed or owned (never both); `aiohttp` only (no `requests`); `py.typed` marker required; zero strict-mode type errors
**Scale/Scope**: Single-process; Marvin API cap of 1440 calls/day is the binding ceiling; client handles 1–10 concurrent HA coroutines

## Constitution Check

*No project constitution configured for py-amazing-marvin. Gates derived from spec requirements instead.*

**Gate 1 — Blocking I/O**: No `requests`, `urllib`, or `open()` calls in library hot paths. ✅ Enforced by FR-005.
**Gate 2 — No global state**: `MarvinClient` holds all mutable state (rate limiter, session). Module level is constants only. ✅ Enforced by FR-004.
**Gate 3 — Type safety**: Zero strict-mode errors, `py.typed` present, no public `Any`-typed returns. ✅ Enforced by FR-016/017/SC-003.
**Gate 4 — Offline tests**: Full test suite runs without network; `aioresponses` mocks all HTTP. ✅ Enforced by FR-021/SC-006.
**Gate 5 — PyPI publishable**: `pyproject.toml`, MIT `LICENSE`, `py.typed`, no `requests` in dependency tree. ✅ Enforced by FR-022/SC-005.

All gates pass.

## Project Structure

### Documentation (this feature)

```text
specs/001-py-amazing-marvin/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   ├── public-api.md    ← Python method signatures (all endpoints)
│   └── exceptions.md    ← exception hierarchy contract
└── tasks.md             ← Phase 2 output (created by /speckit-tasks, not this command)
```

### Source Code (repository root)

```text
src/
└── amazing_marvin/
    ├── __init__.py        # re-exports: MarvinClient, all exceptions, all models
    ├── client.py          # MarvinClient flat class — all endpoint methods
    ├── models.py          # dataclasses for every Marvin entity
    ├── exceptions.py      # MarvinAPIError, MarvinAuthError, MarvinRateLimitError,
    │                      #   MarvinNotFoundError
    └── _throttle.py       # internal asyncio-based rate limiter (not public API)

tests/
├── conftest.py            # shared fixtures: mock session, client factory
├── test_auth.py           # FR-001/002 — token modes, pre-flight auth check
├── test_lifecycle.py      # FR-003/004 — session ownership, context manager, no global state
├── test_errors.py         # FR-006/007/008 — exception hierarchy, error mapping
├── test_throttle.py       # FR-009/010/011/012 — rate limiter, daily reset, concurrent
├── test_timezone.py       # FR-013/014/015 — tz_offset default, per-call override, midnight
├── test_endpoints.py      # FR-018/019 — one test per endpoint group, includes experimental
└── test_models.py         # FR-017 — typed models, unknown-field discard

pyproject.toml             # build system, metadata, dependencies, tool config
LICENSE                    # MIT
README.md                  # usage, auth setup, HA integration example
```

**Structure Decision**: `src/` layout (PEP 517/518 best practice; prevents accidental import of source tree during tests). Single package `amazing_marvin`. All Marvin entity types in one `models.py` to keep cross-references simple at this scale (~15 entity types). Internal `_throttle.py` is private by convention; consumers do not import it directly.

## Implementation Phases

### Phase 1 — Core infrastructure

Build the skeleton that all endpoints will use. No endpoint methods yet.

**Files to create**:
- `pyproject.toml`
- `src/amazing_marvin/__init__.py` (stubs only)
- `src/amazing_marvin/exceptions.py` — full exception hierarchy
- `src/amazing_marvin/models.py` — all dataclasses (can be populated before HTTP works)
- `src/amazing_marvin/_throttle.py` — `_Throttler` class
- `src/amazing_marvin/client.py` — `MarvinClient.__init__`, `__aenter__`, `__aexit__`, `_request`
- `tests/conftest.py`, `tests/test_auth.py`, `tests/test_lifecycle.py`, `tests/test_errors.py`, `tests/test_throttle.py`, `tests/test_timezone.py`, `tests/test_models.py`

**Key decisions**:

`MarvinClient` constructor signature:
```python
def __init__(
    self,
    *,
    api_token: str | None = None,
    full_access_token: str | None = None,
    tz_offset: int = 0,
    throttle: bool = False,
    session: aiohttp.ClientSession | None = None,
) -> None
```

Session ownership:
- `session` supplied → `_owns_session = False`; client never closes it
- `session` is None → client creates one lazily in `__aenter__`; `_owns_session = True`; `__aexit__` closes it

`_request` internal coroutine:
```python
async def _request(
    self,
    method: str,
    path: str,
    *,
    auth: Literal["api", "full"],
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    tz_override: int | None = None,
) -> Any
```
Sequence: pre-flight auth check → throttler acquire (if enabled) → aiohttp call → status-to-exception mapping → JSON decode → return raw parsed object.

**TDD sequence**: exceptions → models skeleton → throttler → client constructor + lifecycle → `_request` error mapping.

### Phase 2 — Read-only endpoints (api_token)

Implement all endpoints accessible with `X-API-Token`. Each method is a thin wrapper around `_request`.

| Method | HTTP | Path | Experimental |
|---|---|---|---|
| `test_credentials()` | POST | `/test` | No |
| `get_today_items(*, tz_offset=None)` | GET | `/todayItems` | No |
| `get_due_items(*, by=None, tz_offset=None)` | GET | `/dueItems` | No |
| `get_categories()` | GET | `/categories` | No |
| `get_labels()` | GET | `/labels` | No |
| `get_children(parent_id)` | GET | `/children` | Yes |
| `add_task(title, **kwargs)` | POST | `/addTask` | No |
| `mark_done(task_id, done=True, *, tz_offset=None)` | POST | `/markDone` | Yes |
| `add_project(title, **kwargs)` | POST | `/addProject` | No |
| `add_event(title, start, **kwargs)` | POST | `/addEvent` | Yes |
| `get_today_time_blocks()` | GET | `/todayTimeBlocks` | Yes |
| `start_tracking(task_id)` | POST | `/track` | No |
| `stop_tracking(task_id)` | POST | `/track` | No |
| `get_time_tracks(task_ids)` | POST | `/tracks` | No |
| `get_tracked_item()` | GET | `/trackedItem` | No |
| `get_kudos()` | GET | `/kudos` | No |
| `get_me()` | GET | `/me` | No |
| `get_goals()` | GET | `/goals` | No |
| `get_habits()` | GET | `/habits` | Yes |
| `get_habit(habit_id)` | GET | `/habit` | Yes |
| `update_habit(habit_id, action, **kwargs)` | POST | `/updateHabit` | Yes |
| `claim_reward_points(points, *, task_id=None)` | POST | `/claimRewardPoints` | No |
| `unclaim_reward_points(*, item_id, date=None)` | POST | `/unclaimRewardPoints` | No |
| `spend_reward_points(points, *, date=None)` | POST | `/spendRewardPoints` | No |
| `set_reminders(reminders)` | POST | `/reminder/set` | No |
| `delete_reminders(reminder_ids)` | POST | `/reminder/delete` | No |

**File**: `src/amazing_marvin/client.py` (add methods), `tests/test_endpoints.py`

### Phase 3 — Full-access endpoints

Implement endpoints requiring `X-Full-Access-Token`:

| Method | HTTP | Path | Experimental |
|---|---|---|---|
| `get_reminders()` | GET | `/reminders` | No |
| `delete_all_reminders()` | POST | `/reminder/deleteAll` | No |
| `reset_reward_points()` | POST | `/resetRewardPoints` | No |
| `get_doc(doc_id)` | GET | `/doc` | Yes |
| `create_doc(data)` | POST | `/doc/create` | Yes |
| `update_doc(doc_id, rev, data)` | POST | `/doc/update` | Yes |
| `delete_doc(doc_id, rev)` | POST | `/doc/delete` | Yes |
| `get_habits_raw()` | GET | `/habits?raw=1` | Yes |

**Note on doc endpoints**: Return `MarvinDocument(id, rev, data)` — a typed container that keeps `data: dict[str, Any]` internal. This avoids raw `dict` crossing the public surface while acknowledging the schema is dynamic per document type.

**File**: `src/amazing_marvin/client.py` (add methods), extend `tests/test_endpoints.py`

### Phase 4 — Packaging and publication prep

- Complete `pyproject.toml` with project metadata, classifiers, Python version constraint
- Add `py.typed` marker inside `src/amazing_marvin/`
- Update `README.md` — auth setup, 20-line HA usage snippet, pyproject install snippet
- Lint / type-check gate: `ruff check src/ tests/` + `mypy --strict src/`

## Throttler Design

```text
_Throttler:
  _lock: asyncio.Lock           ← coordinates across coroutines
  _last_request_at: float       ← monotonic time of last dispatched request
  _daily_count: int
  _daily_date: str              ← YYYY-MM-DD in user's local tz

BURST_INTERVAL = 3.0            ← seconds
DAILY_CAP = 1440

async acquire(tz_offset: int):
  async with _lock:
    today = _local_date(tz_offset)
    if today != _daily_date:
      _daily_count = 0; _daily_date = today
    if _daily_count >= DAILY_CAP:
      raise MarvinRateLimitError(daily_cap_exceeded=True)
    wait = max(0.0, _last_request_at + BURST_INTERVAL - monotonic())
    if wait > 0: await asyncio.sleep(wait)
    _last_request_at = monotonic()
    _daily_count += 1
```

Lock ensures no double-spend across concurrent coroutines (FR-010). Daily rollover checked on every acquire (FR-012).

## Error Mapping

| HTTP status / condition | Exception raised |
|---|---|
| 401, 403 | `MarvinAuthError(status=N)` |
| 404 | `MarvinNotFoundError(status=404)` |
| 429 | `MarvinRateLimitError(retry_after=N, daily_cap_exceeded=False)` |
| 5xx | `MarvinAPIError(status=N, cause=ClientResponseError)` |
| Connection error, timeout | `MarvinAPIError(cause=ClientError)` |
| Non-JSON / schema violation | `MarvinAPIError(raw_body=bytes)` |

No automatic retries on any condition (clarification Q1 — wrap and raise always).

## Timezone Handling

- `tz_offset` stored as `int` (minutes east of UTC, matching Marvin's convention; default `0` = UTC).
- "Today" computation: `datetime.utcnow() + timedelta(minutes=tz_offset)` → `.date().isoformat()`.
- Per-call override: keyword arg `tz_offset` shadows client default for that call only.
- `timeZoneOffset` passed to Marvin on mutating calls that accept it (value in minutes).
- Throttler daily rollover uses the same `_local_date(tz_offset)` helper function.

## Complexity Tracking

*No constitution violations. No complexity justification required.*
