# Research: py-amazing-marvin

**Phase 0 output** | Sourced from: [MarvinAPI wiki](https://github.com/amazingmarvin/MarvinAPI/wiki) (cloned locally to `/tmp/marvin-wiki` for accurate enumeration)

---

## 1. API Base Configuration

**Decision**: Base URL is `https://serv.amazingmarvin.com/api`. All paths are relative to this.
**Rationale**: Confirmed from wiki `Marvin-API.md`.
**Note**: No staging environment documented. Credentials obtained from [app.amazingmarvin.com/pre?api](https://app.amazingmarvin.com/pre?api).

---

## 2. Authentication

**Decision**: Two headers, mutually compatible (client may hold both simultaneously):

| Token type | Header | Scope |
|---|---|---|
| API token | `X-API-Token` | Create tasks/projects/events, all read endpoints, time tracking, habits, rewards, reminders (set/delete) |
| Full access token | `X-Full-Access-Token` | Document CRUD (`/doc/*`), `GET /reminders`, `POST /resetRewardPoints`, `GET /habits?raw=1` |

**Rationale**: Confirmed from wiki credentials section and per-endpoint annotations.
**Correction from subagent**: The subagent described `resetRewardPoints` as using `X-FULL-ACCESS-TOKEN` (uppercase header in example) but the canonical header name is `X-Full-Access-Token`.

---

## 3. Rate Limits

**Decision**:
- Burst: **1 query per 3 seconds** (for read/query endpoints)
- Item creation: **1 item per second** (separate from query burst)
- Daily cap: **1440 queries/day** (not documented as items)

**Rationale**: From wiki. Note: the wiki distinguishes "item creation" rate (1/s) from "query" rate (1/3s). For safety, the throttler will apply the 3-second window to all calls (the more conservative limit). This prevents any category from tripping the rate limit.

**Alternatives considered**: Track two separate buckets (item-create vs query). Rejected — adds complexity with minimal benefit given the HA morning-routine use case that makes a handful of calls per session.

---

## 4. Authoritative Endpoint List (from wiki)

### Key corrections from subagent vs canonical wiki

| Endpoint | Subagent said | Wiki actually says |
|---|---|---|
| `POST /markDone` | body key `taskId` | body key `itemId` |
| `POST /doc/update` | `_id` + `_rev` + fields | `itemId` + `setters` array |
| `POST /doc/delete` | `_id` + `_rev` | `itemId` only |
| `GET /todayItems` | no date param | supports `?date=YYYY-MM-DD` or `X-Date` header |
| `GET /dueItems` | `date` param | `by` param (`YYYY-MM-DD`) |
| `POST /track` | action `"start"/"stop"` | action `"START"/"STOP"` (uppercase) |
| `GET /habit` | `?habitId=abc` | `?id=abc` |
| `POST /reminder/set` | single reminder object | array of reminder objects under key `reminders` |
| `POST /reminder/delete` | `reminderId` string | `reminderIds` string array |
| `GET /kudos` | `{level, nextLevelProgress, totalPoints}` | `{kudos, level, kudosRemaining}` |
| `GET /me` | detailed profile struct | returns Go `Profile` struct (see data-model.md) |

### Complete canonical endpoint table (27 unique endpoints)

| # | Method | Path | Auth | Experimental | Notes |
|---|---|---|---|---|---|
| 1 | POST | `/test` | api | No | Returns `"OK"` |
| 2 | POST | `/addTask` | api | No | Title autocomplete unless `X-Auto-Complete: false` |
| 3 | POST | `/markDone` | api | Yes | Body: `{itemId, timeZoneOffset?}` |
| 4 | POST | `/addProject` | api | No | Same shape as addTask |
| 5 | POST | `/addEvent` | api | Yes | `{title, note?, length?, start}` |
| 6 | GET | `/doc` | full | No | `?id=docId`; returns full document |
| 7 | POST | `/doc/update` | full | Yes | `{itemId, setters: [{key, val}]}` |
| 8 | POST | `/doc/create` | full | Yes | `{_id?, db, title, ...}` |
| 9 | POST | `/doc/delete` | full | Yes | `{itemId}` |
| 10 | GET | `/trackedItem` | api | No | Returns current task or null-like |
| 11 | GET | `/children` | api | Yes | `?parentId=X` or `X-Parent-Id` header |
| 12 | GET | `/todayItems` | api | No | `?date=YYYY-MM-DD` or `X-Date` header |
| 13 | GET | `/dueItems` | api | No | `?by=YYYY-MM-DD` |
| 14 | GET | `/todayTimeBlocks` | api | Yes | `?date=YYYY-MM-DD` or `X-Date` header |
| 15 | GET | `/categories` | api | No | Returns array of Category |
| 16 | GET | `/labels` | api | No | Returns array of Label |
| 17 | POST | `/track` | api | No | `{taskId, action: "START"\|"STOP"}`; alias `/time` |
| 18 | POST | `/tracks` | api | No | `{taskIds: [...]}` → time data; alias `/times` |
| 19 | POST | `/claimRewardPoints` | api | No | `{points, itemId, date, op: "CLAIM"}` |
| 20 | POST | `/unclaimRewardPoints` | api | No | `{itemId, date, op: "UNCLAIM"}` |
| 21 | POST | `/spendRewardPoints` | api | No | `{points, date, op: "SPEND"}` |
| 22 | POST | `/resetRewardPoints` | full | No | Returns user profile |
| 23 | GET | `/kudos` | api | No | `{kudos, level, kudosRemaining}` |
| 24 | GET | `/me` | api | No | Returns Go `Profile` struct |
| 25 | GET | `/reminders` | full | No | Returns `Reminder[]` |
| 26 | POST | `/reminder/set` | api | No | `{reminders: Reminder[]}` → `"OK"` |
| 27 | POST | `/reminder/delete` | api | No | `{reminderIds: string[]}` → `"OK"` |
| 28 | POST | `/reminder/deleteAll` | full | No | → `"OK"` |
| 29 | GET | `/goals` | api | No | Returns `Goal[]` |
| 30 | POST | `/updateHabit` | api | Yes | Three modes: record, undo, rewrite |
| 31 | GET | `/habit` | api | Yes | `?id=habitId` |
| 32 | GET | `/habits` | api | Yes | Without `?raw=1` |
| 33 | GET | `/habits` | full | Yes | With `?raw=1` (full access required for raw) |

**Total unique paths**: 28 (habits with/without raw counted separately for auth purposes).

---

## 5. aiohttp Session Ownership Pattern

**Decision**: Two modes, selected at construction time:
- **Borrowed session**: caller passes `session: aiohttp.ClientSession`; client never calls `session.close()`
- **Owned session**: client creates session in `__aenter__`; closes in `__aexit__` only

**Rationale**: HA shares one `aiohttp.ClientSession` per integration and managing its lifecycle. The borrowed-session mode is the primary HA pattern. Owned mode is provided as a convenience for non-HA callers and tests.

**Alternatives considered**: Always create a new session per request. Rejected — session reuse is important for connection pooling in HA.

---

## 6. Python Async Rate Limiter Pattern

**Decision**: Single `asyncio.Lock` + monotonic clock (`time.monotonic()`); check-then-sleep inside the lock.

**Rationale**: The lock serialises access so concurrent coroutines queue up rather than double-spending the burst window. Using `time.monotonic()` avoids wall-clock skew from system time changes.

**Alternatives considered**:
- `asyncio.Semaphore` with a cleanup task: more complex, unnecessary for the 1-req/3s pattern.
- `asyncio.Queue` with a producer that releases tokens at 3s intervals: correct but over-engineered for this use case.

---

## 7. Typed Dataclass Design

**Decision**: Use `@dataclass` with `__post_init__` that strips unknown keys from `kwargs` before setting fields. No `dataclasses_json` or Pydantic dependency (keeps the dependency footprint minimal for HA).

**Pattern**:
```python
@dataclass
class Task:
    _id: str
    title: str
    done: bool = False
    # ... all documented fields with Optional types ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})
```

**Rationale**: `from_dict` pattern silently discards unknown keys (clarification Q4). No third-party serialisation library needed. Works with `mypy --strict` when field types are annotated.

**Alternatives considered**:
- Pydantic v2: excellent validation, but adds ~4 MB to the dependency footprint which HA consumers will have to install alongside HA's own Pydantic pin.
- `dataclasses_json`: lighter but still a dependency; `from_dict` pattern achieves the same with zero deps.

---

## 8. pyproject.toml Conventions (HA-compatible)

**Decision**: PEP 517 with `hatchling` as build backend; `src/` layout; `py.typed` in package root.

**Key metadata**:
```toml
[project]
name = "py-amazing-marvin"
requires-python = ">=3.12"
dependencies = ["aiohttp>=3.9"]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.23", "aioresponses>=0.7", "mypy>=1.9", "ruff>=0.4"]
```

**Rationale**: `hatchling` is a modern, zero-config build backend that handles `src/` layout and `py.typed` automatically. `aiohttp>=3.9` is the minimum that supports the required features and is compatible with HA 2024.x+.

**Alternatives considered**: `setuptools` with `setup.cfg` — heavier, less declarative. `flit` — simpler but less flexible for future needs.

---

## 9. Special API Behaviours (Implementation Notes)

1. **Title autocompletion**: `POST /addTask` and `/addProject` auto-parse title for `+today`, `#Category`, `@label`. Disable with `X-Auto-Complete: false` header. The client should expose this as a boolean `auto_complete=True` parameter.

2. **`timeZoneOffset` on addTask/addProject**: Prevents day-boundary scheduling errors. The client `add_task()` and `add_project()` must automatically include the active `tz_offset` value.

3. **Track endpoint alias**: `/track` has alias `/time`; `/tracks` has alias `/times`. Use the canonical paths; aliases are for browser extension compatibility.

4. **trackedItem response**: Returns the currently tracked task object (or possibly null/empty). The wiki example shows full Task-like shape. Treat as `Task | None`.

5. **doc/update setters pattern**: The recommended pattern from the wiki is to use `fieldUpdates.FIELD` setters for conflict resolution. The library exposes this exactly as documented — raw `setters` list — without adding higher-level helpers.

6. **Reward points endpoints**: All three (`claim`, `unclaim`, `spend`) return the user `Profile` document (not a balance-only object). Model the return type as `AccountProfile`.

7. **Habits raw mode**: `GET /habits?raw=1` requires `X-Full-Access-Token`. Expose as a separate `get_habits_raw()` method that explicitly requires full access.

8. **markDone known gaps**: The wiki marks several recurring-task edge cases as not yet implemented (e.g., repeat-after-X-days subtasks). The library should not paper over these — it calls the endpoint and surfaces whatever the server returns.
