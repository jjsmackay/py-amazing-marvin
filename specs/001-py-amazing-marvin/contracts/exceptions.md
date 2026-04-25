# Contract: Exception Hierarchy

**File**: `src/amazing_marvin/exceptions.py`

## Class Hierarchy

```
BaseException
└── Exception
    └── MarvinAPIError                    ← base for all library errors
        ├── MarvinAuthError               ← 401 / 403, or missing token detected pre-flight
        ├── MarvinRateLimitError          ← 429, or daily cap exceeded by throttler
        └── MarvinNotFoundError           ← 404
```

## Class Signatures

```python
class MarvinAPIError(Exception):
    """Base class for all py-amazing-marvin errors.

    Attributes:
        status: HTTP status code, or None for pre-HTTP errors.
        cause: The underlying exception that triggered this error, or None.
        raw_body: Raw response body bytes when JSON parsing failed, or None.
    """
    def __init__(
        self,
        message: str = "",
        *,
        status: int | None = None,
        cause: BaseException | None = None,
        raw_body: bytes | None = None,
    ) -> None: ...

    status: int | None
    cause: BaseException | None
    raw_body: bytes | None


class MarvinAuthError(MarvinAPIError):
    """Raised when authentication fails or a required token is not configured.

    Attributes:
        required_token: Which token type was missing/invalid: "api" or "full".
    """
    def __init__(
        self,
        message: str = "",
        *,
        status: int | None = None,
        cause: BaseException | None = None,
        required_token: str | None = None,
    ) -> None: ...

    required_token: str | None  # "api" or "full"


class MarvinRateLimitError(MarvinAPIError):
    """Raised when the Marvin API rate limit is hit (429) or the throttler
    detects the daily cap has been reached.

    Attributes:
        retry_after: Value of the Retry-After response header in seconds, or None.
        daily_cap_exceeded: True if the 1440/day cap was hit (vs burst window).
    """
    def __init__(
        self,
        message: str = "",
        *,
        status: int | None = None,
        cause: BaseException | None = None,
        retry_after: float | None = None,
        daily_cap_exceeded: bool = False,
    ) -> None: ...

    retry_after: float | None
    daily_cap_exceeded: bool


class MarvinNotFoundError(MarvinAPIError):
    """Raised when the Marvin API returns 404."""
    def __init__(
        self,
        message: str = "",
        *,
        status: int = 404,
        cause: BaseException | None = None,
    ) -> None: ...
```

## Usage Contract

- All four classes are importable from `amazing_marvin` directly:
  ```python
  from amazing_marvin import MarvinAPIError, MarvinAuthError, MarvinRateLimitError, MarvinNotFoundError
  ```
- `except MarvinAPIError` catches all library errors (catch-all pattern).
- No exception is ever re-raised as a bare `aiohttp` exception across the public boundary.
- Pre-flight auth checks (missing token) raise `MarvinAuthError` with `status=None` and `required_token` set.
