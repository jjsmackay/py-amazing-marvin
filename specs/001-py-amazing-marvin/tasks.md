# Tasks: py-amazing-marvin

**Input**: Design documents from `specs/001-py-amazing-marvin/`
**Branch**: `001-py-amazing-marvin`
**Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md) | **Contracts**: [contracts/](contracts/)

**Tests**: Included — FR-021 mandates a `pytest-asyncio` test suite covering auth, rate limits, timezone, error mapping, and all endpoint groups.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared state)
- **[Story]**: Which user story this task belongs to (US1–US5)
- All paths relative to repository root

---

## Phase 1: Setup

**Purpose**: Project scaffolding and tooling configuration. No implementation code — just structure and config.

- [ ] T001 Create `src/amazing_marvin/` package directory with empty `__init__.py` and `py.typed` marker
- [ ] T002 Create `tests/` directory with empty `conftest.py` and `__init__.py`
- [ ] T003 [P] Write `pyproject.toml` with `[build-system]` (hatchling), `[project]` metadata (name, version, requires-python=">=3.12", dependencies=["aiohttp>=3.9"]), and `[project.optional-dependencies] dev` (pytest, pytest-asyncio, aioresponses, mypy, ruff)
- [ ] T004 [P] Write `pyproject.toml` tool sections: `[tool.pytest.ini_options]` (asyncio_mode="auto", testpaths=["tests"]), `[tool.mypy]` (strict=true), `[tool.ruff]` (line-length=100, select=["E","F","I"])
- [ ] T005 [P] Create `LICENSE` (MIT, year 2026, copyright jjsmackay) and update `README.md` placeholder

**Checkpoint**: `pip install -e ".[dev]"` succeeds; `pytest --collect-only` exits 0 with no errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that ALL user stories depend on. Must be complete before any user story phase begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T006 Implement `src/amazing_marvin/exceptions.py` — full exception hierarchy: `MarvinAPIError(Exception)` with `status`, `cause`, `raw_body` attributes; `MarvinAuthError(MarvinAPIError)` with `required_token`; `MarvinRateLimitError(MarvinAPIError)` with `retry_after`, `daily_cap_exceeded`; `MarvinNotFoundError(MarvinAPIError)`. See [contracts/exceptions.md](contracts/exceptions.md).
- [ ] T007 [P] Implement `src/amazing_marvin/models.py` — all 14 dataclasses: `Subtask`, `Task`, `Category`, `Label`, `CalendarEvent`, `TimeBlock`, `TrackingResult`, `TimeTrack`, `Kudos`, `AccountProfile`, `Reminder`, `Goal`, `GoalSection`, `Habit`, `MarvinDocument`. Each class has a `from_dict(data: dict[str, Any]) -> Self` classmethod that silently discards unknown keys. Use `dataclasses.field(default_factory=...)` for list/dict defaults. See [data-model.md](data-model.md) for all field names and types.
- [ ] T008 [P] Implement `src/amazing_marvin/_throttle.py` — `_Throttler` class with `asyncio.Lock`, `_last_request_at: float`, `_daily_count: int`, `_daily_date: str`; `async def acquire(tz_offset: int) -> None` that enforces `BURST_INTERVAL=3.0s` and `DAILY_CAP=1440` per the throttler design in [plan.md](plan.md). Raises `MarvinRateLimitError(daily_cap_exceeded=True)` at daily cap. Uses `time.monotonic()` for burst timing.
- [ ] T009 Implement `src/amazing_marvin/client.py` — `MarvinClient.__init__` (keyword-only args: `api_token`, `full_access_token`, `tz_offset=0`, `throttle=False`, `session=None`), `__aenter__`, `__aexit__` (session ownership: creates/closes only if `_owns_session=True`), and `_request(method, path, *, auth, json=None, params=None, headers=None, tz_override=None) -> Any`. `_request` must: (1) check token present pre-flight raising `MarvinAuthError(required_token=...)`, (2) call throttler if enabled, (3) dispatch `aiohttp`, (4) map 401/403→`MarvinAuthError`, 404→`MarvinNotFoundError`, 429→`MarvinRateLimitError(retry_after=...)`, 5xx→`MarvinAPIError`, `aiohttp.ClientError`→`MarvinAPIError(cause=...)`, non-JSON body→`MarvinAPIError(raw_body=...)`. No automatic retries on any condition.
- [ ] T010 Write `tests/conftest.py` — shared `pytest-asyncio` fixtures: `mock_session` (an `aiohttp.ClientSession`-like mock compatible with `aioresponses`), `api_client` factory (returns `MarvinClient(api_token="test-api", session=mock_session)`), `full_client` factory (both tokens), `throttled_client` factory (throttle=True).
- [ ] T011 Write `tests/test_models.py` — tests for `from_dict` on all model classes: unknown keys silently discarded (FR-017); known camelCase fields mapped to snake_case attributes; list/dict fields default to empty collections; `MarvinDocument.from_dict` correctly separates `_id`/`_rev` from `data`.

**Checkpoint**: `pytest tests/test_models.py` passes. `mypy --strict src/amazing_marvin/exceptions.py src/amazing_marvin/models.py src/amazing_marvin/_throttle.py` exits 0.

---

## Phase 3: User Story 1 — Read Tasks from a HA Integration (Priority: P1) 🎯 MVP

**Goal**: A Home Assistant integration developer can authenticate, fetch today's tasks with timezone-aware date resolution, and receive properly typed `Task` objects — using a borrowed session with no lifecycle side effects.

**Independent Test**: With a mocked session, call `get_today_items(tz_offset=-300)` at 23:30 UTC and confirm it queries for the local-date day (day N−1). Confirm auth error is raised before any HTTP call when `api_token` is absent.

### Tests for User Story 1

- [ ] T012 [P] [US1] Write `tests/test_auth.py` — api_token mode: test pre-flight `MarvinAuthError` when `api_token=None` on an api-token-required method; test valid api_token sends correct `X-API-Token` header; test full-access method raises `MarvinAuthError(required_token="full")` when only api_token configured. Uses `aioresponses`.
- [ ] T013 [P] [US1] Write `tests/test_lifecycle.py` — session ownership: borrowed session is never closed after calls; owned session (no `session` arg, used as context manager) is created in `__aenter__` and closed exactly once in `__aexit__`; calling methods without entering context manager raises meaningful error. Verify no module-level mutable state by instantiating two clients with different tokens and confirming calls route to correct credential.
- [ ] T014 [P] [US1] Write `tests/test_timezone.py` — tz_offset: `get_today_items()` with default `tz_offset=0` sends today's UTC date; with `tz_offset=-300` at 23:30 UTC sends previous day; per-call override does not mutate `client.tz_offset`; `get_today_items(tz_offset=840)` (UTC+14) at 23:00 UTC sends next day. Cover UTC-12 to UTC+14 range (SC-007).

### Implementation for User Story 1

- [ ] T015 [US1] Add read endpoint methods to `src/amazing_marvin/client.py`: `test_credentials()→bool`, `get_today_items(*, tz_offset=None)→list[Task]`, `get_due_items(*, by=None, tz_offset=None)→list[Task]`. `get_today_items` sends date as `X-Date: YYYY-MM-DD` header computed from active `tz_offset`. `get_due_items` sends `?by=YYYY-MM-DD`. Both parse response list via `Task.from_dict`. See [research.md](research.md) §4 for exact query parameters.
- [ ] T016 [P] [US1] Add to `src/amazing_marvin/client.py`: `get_categories()→list[Category]`, `get_labels()→list[Label]`, `get_me()→AccountProfile`, `get_kudos()→Kudos`. Straightforward GET wrappers using api_token auth.
- [ ] T017 [P] [US1] Update `src/amazing_marvin/__init__.py` — export all public symbols: `MarvinClient`, four exception classes, all 15 model classes. See [contracts/public-api.md](contracts/public-api.md) `__all__` list.

**Checkpoint**: `pytest tests/test_auth.py tests/test_lifecycle.py tests/test_timezone.py` pass. A script calling `get_today_items()` against a mocked session returns a typed `list[Task]` without blocking.

---

## Phase 4: User Story 2 — Mark a Subtask Complete (Priority: P1)

**Goal**: The HA integration can call `mark_done(item_id, done=True)` and receive a typed `Task` with `done=True`, or a typed error if the ID is wrong or the wrong token is configured — with no silent failures and no event-loop blocking.

**Independent Test**: Call `mark_done("known-id")` against a mocked 200 response and confirm returned `Task.done=True`. Call with a mocked 404 and confirm `MarvinNotFoundError` carrying the status. Call with only `api_token` configured on a method requiring full access and confirm `MarvinAuthError` before any HTTP call.

### Tests for User Story 2

- [ ] T018 [P] [US2] Write `tests/test_errors.py` — error mapping: 401→`MarvinAuthError(status=401)`; 403→`MarvinAuthError(status=403)`; 404→`MarvinNotFoundError(status=404)`; 429 with `Retry-After: 5`→`MarvinRateLimitError(retry_after=5.0, daily_cap_exceeded=False)`; 500→`MarvinAPIError(status=500)` with cause attached; `aiohttp.ClientConnectorError`→`MarvinAPIError(cause=...)` with no HTTP status; non-JSON `text/plain` body→`MarvinAPIError(raw_body=bytes)`. Verify no exception is a bare `aiohttp` exception.

### Implementation for User Story 2

- [ ] T019 [US2] Add to `src/amazing_marvin/client.py`: `mark_done(item_id, done=True, *, tz_offset=None)→Task` — `POST /markDone` with body `{"itemId": item_id, "timeZoneOffset": active_tz}`, auth=api_token, parses response via `Task.from_dict`. See [research.md](research.md) §4 correction: field is `itemId` not `taskId`.
- [ ] T020 [P] [US2] Add to `src/amazing_marvin/client.py`: `add_task(title, *, auto_complete=True, tz_offset=None, **kwargs)→Task` and `add_project(title, *, auto_complete=True, tz_offset=None, **kwargs)→Category`. Both POST to `/addTask`/`/addProject`. Send `X-Auto-Complete: false` header when `auto_complete=False`. Active `tz_offset` always included as `timeZoneOffset` in body. Auth=api_token.
- [ ] T021 [P] [US2] Add to `src/amazing_marvin/client.py`: `get_children(parent_id)→list[Task]` (experimental) — `GET /children?parentId={parent_id}`, auth=api_token. Adds docstring noting experimental status and that only open items are returned.

**Checkpoint**: `pytest tests/test_errors.py` passes. `mark_done` integration path returns a typed `Task` or raises a typed exception — no raw `aiohttp` exceptions escape.

---

## Phase 5: User Story 3 — Rate Limit Survival (Priority: P1)

**Goal**: With `throttle=True`, 5+ rapid calls complete sequentially without tripping Marvin's rate limit. With `throttle=False`, a server-issued 429 surfaces a `MarvinRateLimitError` with `retry_after` and `daily_cap_exceeded` metadata. The rate limiter is safe under concurrent coroutines.

**Independent Test**: With throttle=True and a mock that tracks call timestamps, issue 5 concurrent calls and confirm each is spaced ≥3 s apart. Then with throttle=False, issue a call against a mocked 429 (Retry-After: 10) and confirm `MarvinRateLimitError(retry_after=10.0)` is raised.

### Tests for User Story 3

- [ ] T022 [US3] Write `tests/test_throttle.py` — throttler tests: (1) burst enforcement: 5 sequential calls via throttler take ≥12 s wall time (mock `asyncio.sleep`); (2) daily cap: after 1440 calls, next `acquire()` raises `MarvinRateLimitError(daily_cap_exceeded=True)`; (3) daily rollover: counter resets when local date changes (pass different `tz_offset` to change `_local_date`); (4) concurrent safety: 10 concurrent coroutines each acquiring the throttler result in sequential call spacing with no double-spend; (5) throttle=False: 429 response raises `MarvinRateLimitError(retry_after=5.0)` immediately without sleeping.

### Implementation for User Story 3

- [ ] T023 [US3] Wire `_Throttler` into `MarvinClient._request` — when `self._throttle=True`, call `await self._throttler.acquire(active_tz_offset)` before dispatching aiohttp. Throttler instance is created in `__init__` when `throttle=True`, else `None`. When `throttle=False` and server returns 429, parse `Retry-After` header (int or HTTP-date) and raise `MarvinRateLimitError(retry_after=parsed, daily_cap_exceeded=False)`.
- [ ] T024 [P] [US3] Add `_local_date(tz_offset: int) -> str` helper to `src/amazing_marvin/_throttle.py` — returns `(datetime.utcnow() + timedelta(minutes=tz_offset)).date().isoformat()`. Used by `_Throttler.acquire` for daily rollover and by `_request` for date header computation (extract as shared utility in a `_utils.py` or inline in both files consistently).

**Checkpoint**: `pytest tests/test_throttle.py` passes. With `throttle=True`, 5 concurrent calls to a mocked endpoint complete in order with no `MarvinRateLimitError` raised. With `throttle=False`, a 429 response raises `MarvinRateLimitError` immediately.

---

## Phase 6: User Story 4 — Full Documented API Surface (Priority: P2)

**Goal**: Every documented endpoint has a corresponding `MarvinClient` method. All experimental endpoints are implemented with stability status in their docstrings. All methods return typed models.

**Independent Test**: Call each endpoint group against mocked responses and confirm: correct HTTP method and path; correct auth header sent; response parsed to correct typed model; experimental methods have "Experimental." in their docstring.

### Tests for User Story 4

- [ ] T025 [US4] Write `tests/test_endpoints.py` — one test per endpoint or endpoint group: test_credentials, get_today_items, get_due_items, get_categories, get_labels, get_children, add_task (with and without auto_complete), mark_done, add_project, add_event, get_today_time_blocks, start_tracking, stop_tracking, get_time_tracks, get_tracked_item, get_kudos, get_me, get_goals, get_habits, get_habit, update_habit (record/undo/rewrite), claim_reward_points, unclaim_reward_points, spend_reward_points, reset_reward_points (full token), get_reminders (full token), set_reminders, delete_reminders, delete_all_reminders (full token), get_doc, create_doc, update_doc, delete_doc, get_habits_raw (full token). Confirm correct paths, auth headers, and return types using `aioresponses`.

### Implementation for User Story 4

- [ ] T026 [P] [US4] Add calendar methods to `src/amazing_marvin/client.py`: `add_event(title, start, *, note=None, length=None)→CalendarEvent` (experimental), `get_today_time_blocks(*, tz_offset=None)→list[TimeBlock]` (experimental). Auth=api_token.
- [ ] T027 [P] [US4] Add time tracking methods: `start_tracking(task_id)→TrackingResult`, `stop_tracking(task_id)→TrackingResult`, `get_time_tracks(task_ids)→list[TimeTrack]`, `get_tracked_item()→Task|None`. Auth=api_token. `start_tracking`/`stop_tracking` POST to `/track` with `{"taskId": task_id, "action": "START"/"STOP"}` (uppercase — see [research.md](research.md) §4 correction). `get_tracked_item` returns `None` if response is null-like.
- [ ] T028 [P] [US4] Add goals and habits methods: `get_goals()→list[Goal]`, `get_habits()→list[Habit]` (experimental), `get_habit(habit_id)→Habit` (experimental), `get_habits_raw()→list[Habit]` (experimental, full token), `update_habit(habit_id, *, time=None, value=None, undo=False, history=None, update_db=True)→Any` (experimental). Auth=api_token except `get_habits_raw`.
- [ ] T029 [P] [US4] Add rewards methods: `claim_reward_points(points, *, item_id=None, date=None)→AccountProfile`, `unclaim_reward_points(*, item_id, date=None)→AccountProfile`, `spend_reward_points(points, *, date=None)→AccountProfile`, `reset_reward_points()→AccountProfile` (full token). Body structure per [research.md](research.md) §4: `claim` sends `{points, itemId, date, op:"CLAIM"}`.
- [ ] T030 [P] [US4] Add reminder methods: `get_reminders()→list[Reminder]` (full token), `set_reminders(reminders)→bool` — POSTs `{"reminders": [r.to_dict() for r in reminders]}` (need `Reminder.to_dict()` or inline dict construction), `delete_reminders(reminder_ids)→bool` — POSTs `{"reminderIds": reminder_ids}`, `delete_all_reminders()→bool` (full token). Note: `set_reminders` and `delete_reminders` need `Reminder` to be serialisable to dict — add `to_dict()` to `Reminder` dataclass in models.py.
- [ ] T031 [P] [US4] Add document access methods: `get_doc(doc_id)→MarvinDocument`, `create_doc(data)→MarvinDocument`, `update_doc(item_id, setters)→MarvinDocument`, `delete_doc(item_id)→bool`. All require full_access_token. `update_doc` POSTs `{"itemId": item_id, "setters": setters}` (see [research.md](research.md) §4 correction — NOT `_id`+`_rev`+fields). All experimental.
- [ ] T032 [US4] Add `Reminder.to_dict()` method to `src/amazing_marvin/models.py` — serialises `Reminder` back to the API's camelCase JSON format for use in `set_reminders`. Covers the `reminderId`→`reminderId` mapping (no rename needed for Reminder fields that stay camelCase on the wire).

**Checkpoint**: `pytest tests/test_endpoints.py` passes (all 33+ endpoint tests). Inspect output to confirm every method with "experimental" status has "Experimental." in its docstring.

---

## Phase 7: User Story 5 — PyPI Publication (Priority: P2)

**Goal**: The package builds into a valid wheel, installs into a clean virtualenv in <5 s, imports cleanly, includes `py.typed`, has no `requests` in its dependency tree, and carries MIT licence + correct metadata.

**Independent Test**: `pip wheel . -w /tmp/wheel-test && pip install /tmp/wheel-test/py_amazing_marvin-*.whl && python -c "from amazing_marvin import MarvinClient; print('OK')"` in a fresh virtualenv. Then `pip show py-amazing-marvin` shows licence=MIT and requires=aiohttp. `pipdeptree` (or `pip show aiohttp`) confirms no `requests` dep.

### Implementation for User Story 5

- [ ] T033 [US5] Finalise `pyproject.toml` — complete project metadata: `description`, `authors`, `licence = {text="MIT"}`, `classifiers` (Python versions, "Intended Audience :: Developers", "Topic :: Software Development :: Libraries", "License :: OSI Approved :: MIT License", "Framework :: AsyncIO"), `urls` (homepage, source). Confirm `[tool.hatch.build.targets.wheel]` includes `src/` as package root.
- [ ] T034 [P] [US5] Verify `src/amazing_marvin/py.typed` exists (created in T001). Confirm `pyproject.toml` does NOT list it explicitly as a package data file (hatchling includes it automatically from the `src/` layout). Run `mypy --strict src/amazing_marvin/` — must exit 0 with no errors (SC-003).
- [ ] T035 [P] [US5] Write `README.md` — sections: Installation (pip install), Quick Start (20-line HA example from [quickstart.md](quickstart.md)), Auth Setup (where to find tokens in Marvin), Rate Limits note, Timezone handling note, Licence badge. Matches the HA borrowed-session pattern from quickstart.md.
- [ ] T036 [P] [US5] Run `ruff check src/ tests/` and fix any lint errors. Run `pytest --tb=short -q` and confirm full suite passes. Run `pip wheel . -w /tmp/test-wheel` and `pip install --dry-run /tmp/test-wheel/py_amazing_marvin-*.whl` to confirm wheel is valid and `requests` is not in deps.

**Checkpoint**: Clean install succeeds. `from amazing_marvin import MarvinClient` works. `py.typed` present in installed package. No `requests` in dependency tree. `mypy --strict` exits 0.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Verification passes covering the full library that span multiple user stories.

- [ ] T037 [P] Run `pytest --cov=amazing_marvin --cov-report=term-missing tests/` and confirm ≥90% line coverage on `client.py` and `models.py` (SC-006). Identify and fill any coverage gaps.
- [ ] T038 [P] SC-007 day-boundary completeness: extend `tests/test_timezone.py` with parametrised tests covering `tz_offset` values {-720, -300, 0, 330, 540, 840} at T-1s and T+1s of local midnight — confirm "today" flips at the correct moment for each zone.
- [ ] T039 [P] SC-001 ergonomics check: write a minimal script in `tests/test_quickstart.py` that imports `MarvinClient` and executes the HA borrowed-session flow from [quickstart.md](quickstart.md) against mocked responses — must be ≤20 lines of integration code.
- [ ] T040 SC-002 endpoint coverage assertion: write `tests/test_coverage_assertion.py` that inspects `MarvinClient`'s public methods and asserts the count matches the 33 documented endpoints (plus `get_habits_raw` = 34 methods). This acts as a regression guard against accidental endpoint removal.

**Checkpoint**: All 40 tasks complete. `pytest -q` passes. Coverage ≥90%. `mypy --strict` exits 0. `ruff check` exits 0. Wheel builds and installs cleanly.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately.
- **Phase 2 (Foundation)**: Depends on Phase 1. **Blocks all user story phases.**
- **Phase 3 (US1)**: Depends on Phase 2 only. No dependency on US2/US3/US4/US5.
- **Phase 4 (US2)**: Depends on Phase 2. Reuses `_request` error mapping from Phase 2. No dependency on US1.
- **Phase 5 (US3)**: Depends on Phase 2 only (`_Throttler` wired into `_request`). No dependency on US1/US2.
- **Phase 6 (US4)**: Depends on Phase 2 (infrastructure). Benefits from Phase 3–5 completion (error mapping, throttling already wired) but can start after Phase 2 if Phase 3–5 are deferred.
- **Phase 7 (US5)**: Depends on Phase 6 completion (all endpoints must exist before packaging is finalised).
- **Phase 8 (Polish)**: Depends on Phases 3–7 completion.

### User Story Dependencies

- **US1 (P1)**: No inter-story dependency. Can be the sole MVP delivery.
- **US2 (P1)**: No dependency on US1. `mark_done` reuses `_request` and `Task.from_dict` already written in Phase 2/3 but does not require US1's endpoints.
- **US3 (P1)**: No dependency on US1 or US2. `_Throttler` is self-contained.
- **US4 (P2)**: No dependency on US1–3 other than Phase 2 foundation.
- **US5 (P2)**: Depends on US4 (all endpoints must exist).

### Within Each Phase

- Test tasks (T012–T014, T018, T022, T025) should be written **before** or **alongside** implementation — write the test first, confirm it fails, then implement to make it pass.
- Within a phase: [P]-marked tasks can run in parallel; unmarked tasks should run after [P] tasks complete.
- Commit after each [P] group or logical unit.

---

## Parallel Execution Examples

### Phase 2 (Foundation) — run in parallel

```text
Task T007: models.py — all dataclasses
Task T008: _throttle.py — _Throttler
(after T006 exceptions.py: run T009 client.py and T010/T011 tests)
```

### Phase 3 (US1) — run in parallel after Phase 2

```text
Parallel group A (tests):
  Task T012: tests/test_auth.py
  Task T013: tests/test_lifecycle.py
  Task T014: tests/test_timezone.py

Parallel group B (implementation — after T015):
  Task T016: get_categories, get_labels, get_me, get_kudos
  Task T017: __init__.py exports
```

### Phase 6 (US4) — run in parallel after Phase 2

```text
Task T026: add_event, get_today_time_blocks
Task T027: time tracking methods
Task T028: goals, habits methods
Task T029: rewards methods
Task T030: reminder methods
Task T031: document methods
(then T032 Reminder.to_dict, T025 test_endpoints.py)
```

---

## Implementation Strategy

### MVP (US1 only — HA read path)

1. Complete Phase 1 (Setup) → Phase 2 (Foundation)
2. Complete Phase 3 (US1: read tasks)
3. **Stop and validate**: `pytest tests/test_auth.py tests/test_lifecycle.py tests/test_timezone.py` pass; `get_today_items()` returns typed tasks against a mock.
4. HA integration can already import the library and read today's items.

### Full P1 Delivery (US1 + US2 + US3)

1. Phases 1 → 2 → 3 (US1)
2. Phase 4 (US2: mark done) and Phase 5 (US3: rate limiting) can be worked in parallel after Phase 2.
3. All three P1 stories are independently testable; they share only Phase 2 infrastructure.

### Full Library Delivery

1. Phases 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8.
2. Phases 4/5/6 can overlap after Phase 2.
3. Phase 7 (packaging) requires Phase 6 complete.
4. Phase 8 (polish) last.

---

## Notes

- `[P]` tasks operate on different files — safe to parallelise.
- Each `[USN]` label maps directly to a user story in [spec.md](spec.md).
- Every phase ends with a **Checkpoint** — validate independently before proceeding.
- `Reminder.to_dict()` (T032) is a blocker for T030; schedule accordingly.
- `aioresponses` is the recommended mock — compatible with `pytest-asyncio` and `aiohttp`.
- The `_Throttler` uses `asyncio.sleep` internally; mock it in tests with `unittest.mock.patch("asyncio.sleep")` or `freezegun`.
- Do not add network calls to tests under any circumstances — all HTTP must go through `aioresponses`.
