"""Tests for FR-006/007/008 — exception hierarchy and error mapping (T018)."""

from __future__ import annotations

from unittest.mock import patch

import aiohttp
import pytest
from aioresponses import aioresponses

from amazing_marvin.client import MarvinClient
from amazing_marvin.exceptions import (
    MarvinAPIError,
    MarvinAuthError,
    MarvinNotFoundError,
    MarvinRateLimitError,
)

BASE = "https://serv.amazingmarvin.com/api"


@pytest.fixture
def mock_responses():
    with aioresponses() as m:
        yield m


# ---------------------------------------------------------------------------
# HTTP status code mapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_401_raises_marvin_auth_error_status_401(mock_responses):
    """HTTP 401 -> MarvinAuthError(status=401), is instance of MarvinAPIError."""
    mock_responses.post(f"{BASE}/test", status=401)
    async with MarvinClient(api_token="tok") as client:
        with pytest.raises(MarvinAuthError) as exc_info:
            await client.test_credentials()
    err = exc_info.value
    assert err.status == 401
    assert isinstance(err, MarvinAPIError)


@pytest.mark.asyncio
async def test_403_raises_marvin_auth_error_status_403(mock_responses):
    """HTTP 403 -> MarvinAuthError(status=403)."""
    mock_responses.post(f"{BASE}/test", status=403)
    async with MarvinClient(api_token="tok") as client:
        with pytest.raises(MarvinAuthError) as exc_info:
            await client.test_credentials()
    assert exc_info.value.status == 403


@pytest.mark.asyncio
async def test_404_raises_marvin_not_found_error(mock_responses):
    """HTTP 404 -> MarvinNotFoundError(status=404), is instance of MarvinAPIError."""
    mock_responses.get(f"{BASE}/todayItems", status=404)
    async with MarvinClient(api_token="tok") as client:
        with pytest.raises(MarvinNotFoundError) as exc_info:
            await client.get_today_items()
    err = exc_info.value
    assert err.status == 404
    assert isinstance(err, MarvinAPIError)


@pytest.mark.asyncio
async def test_429_raises_rate_limit_error_with_retry_after(mock_responses):
    """HTTP 429 with Retry-After:5 -> MarvinRateLimitError(retry_after=5.0)."""
    mock_responses.post(f"{BASE}/test", status=429, headers={"Retry-After": "5"})
    async with MarvinClient(api_token="tok") as client:
        with pytest.raises(MarvinRateLimitError) as exc_info:
            await client.test_credentials()
    err = exc_info.value
    assert err.status == 429
    assert err.retry_after == 5.0
    assert err.daily_cap_exceeded is False


@pytest.mark.asyncio
async def test_500_raises_marvin_api_error(mock_responses):
    """HTTP 500 -> MarvinAPIError(status=500)."""
    mock_responses.post(f"{BASE}/test", status=500)
    async with MarvinClient(api_token="tok") as client:
        with pytest.raises(MarvinAPIError) as exc_info:
            await client.test_credentials()
    err = exc_info.value
    assert err.status == 500


# ---------------------------------------------------------------------------
# Network error — aiohttp.ClientConnectionError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_client_connection_error_wrapped_as_marvin_api_error():
    """aiohttp.ClientConnectionError -> MarvinAPIError with cause set."""
    connection_error = aiohttp.ClientConnectionError("connection refused")

    async with aiohttp.ClientSession() as real_session:
        client = MarvinClient(api_token="tok", session=real_session)
        # Patch the session.request to raise ClientConnectionError
        with patch.object(real_session, "request") as mock_request:
            mock_request.side_effect = connection_error

            with pytest.raises(MarvinAPIError) as exc_info:
                await client.test_credentials()

    err = exc_info.value
    assert isinstance(err, MarvinAPIError)
    assert not isinstance(err, aiohttp.ClientConnectionError)
    assert err.cause is connection_error


@pytest.mark.asyncio
async def test_raw_aiohttp_exception_does_not_escape():
    """Raw aiohttp exceptions must not escape — only MarvinAPIError subclasses."""
    async with aiohttp.ClientSession() as real_session:
        client = MarvinClient(api_token="tok", session=real_session)
        with patch.object(real_session, "request") as mock_request:
            mock_request.side_effect = aiohttp.ClientConnectionError("no route")

            try:
                await client.test_credentials()
                pytest.fail("Should have raised")
            except MarvinAPIError:
                pass  # correct
            except aiohttp.ClientError:
                pytest.fail("Raw aiohttp exception escaped")


# ---------------------------------------------------------------------------
# Non-JSON body on 200 response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_json_body_200_raises_marvin_api_error(mock_responses):
    """Non-JSON text/plain body on 200 -> MarvinAPIError(raw_body=<bytes>); status=200."""
    mock_responses.post(
        f"{BASE}/test",
        status=200,
        body=b"this is not json",
        content_type="text/plain",
    )
    async with MarvinClient(api_token="tok") as client:
        with pytest.raises(MarvinAPIError) as exc_info:
            await client.test_credentials()
    err = exc_info.value
    # The error may succeed if the text parses as something non-JSON... but "this is not json"
    # will fail JSON parsing. Check that either it succeeded (returned false) or raised.
    # Actually "this is not json" is not valid JSON so it raises.
    assert err.status == 200
    assert err.raw_body == b"this is not json"
