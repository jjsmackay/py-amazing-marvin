"""Exception hierarchy for py-amazing-marvin."""

from __future__ import annotations


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
    ) -> None:
        super().__init__(message)
        self.status = status
        self.cause = cause
        self.raw_body = raw_body


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
    ) -> None:
        super().__init__(message, status=status, cause=cause)
        self.required_token = required_token


class MarvinRateLimitError(MarvinAPIError):
    """Raised when the rate limit is hit (429) or the daily cap is reached.

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
    ) -> None:
        super().__init__(message, status=status, cause=cause)
        self.retry_after = retry_after
        self.daily_cap_exceeded = daily_cap_exceeded


class MarvinNotFoundError(MarvinAPIError):
    """Raised when the Marvin API returns 404."""
