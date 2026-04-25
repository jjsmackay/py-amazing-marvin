"""Tests for FR-001/002 — token modes and pre-flight auth checks (T012)."""

from __future__ import annotations

import pytest
from aioresponses import aioresponses

from amazing_marvin.client import MarvinClient
from amazing_marvin.exceptions import MarvinAPIError, MarvinAuthError

BASE = "https://serv.amazingmarvin.com/api"


@pytest.fixture
def mock_responses():
    with aioresponses() as m:
        yield m


# ---------------------------------------------------------------------------
# Pre-flight checks (before HTTP call)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_token_none_raises_before_http(mock_responses):
    """api_token=None on an api-token-required method raises MarvinAuthError before HTTP."""
    async with MarvinClient(api_token=None) as client:
        with pytest.raises(MarvinAuthError) as exc_info:
            await client.test_credentials()
    assert exc_info.value.required_token == "api"
    # No HTTP calls should have been made
    assert len(mock_responses.requests) == 0


@pytest.mark.asyncio
async def test_full_access_token_none_raises_before_http(mock_responses):
    """full_access_token=None on a full-access method raises MarvinAuthError before HTTP."""
    async with MarvinClient(api_token="tok") as client:
        with pytest.raises(MarvinAuthError) as exc_info:
            await client.reset_reward_points()
    assert exc_info.value.required_token == "full"
    assert len(mock_responses.requests) == 0


@pytest.mark.asyncio
async def test_only_api_token_on_full_access_method_raises(mock_responses):
    """Client with only api_token raises MarvinAuthError for full-access methods."""
    async with MarvinClient(api_token="test-api-token") as client:
        with pytest.raises(MarvinAuthError) as exc_info:
            await client.get_reminders()
    assert exc_info.value.required_token == "full"
    assert len(mock_responses.requests) == 0


# ---------------------------------------------------------------------------
# Valid api_token sends X-API-Token header
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_api_token_sends_header(mock_responses):
    """A valid api_token sends X-API-Token header in the request."""
    mock_responses.post(f"{BASE}/test", payload="OK")
    async with MarvinClient(api_token="my-api-token") as client:
        result = await client.test_credentials()
    assert result is True
    # Verify header was sent
    calls = list(mock_responses.requests.values())
    assert len(calls) == 1
    sent_headers = calls[0][0].kwargs.get("headers", {})
    assert sent_headers.get("X-API-Token") == "my-api-token"


# ---------------------------------------------------------------------------
# 401/403 HTTP responses raise MarvinAuthError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_401_raises_marvin_auth_error(mock_responses):
    """HTTP 401 response raises MarvinAuthError with status=401."""
    mock_responses.post(f"{BASE}/test", status=401)
    async with MarvinClient(api_token="tok") as client:
        with pytest.raises(MarvinAuthError) as exc_info:
            await client.test_credentials()
    assert exc_info.value.status == 401


@pytest.mark.asyncio
async def test_403_raises_marvin_auth_error(mock_responses):
    """HTTP 403 response raises MarvinAuthError with status=403."""
    mock_responses.post(f"{BASE}/test", status=403)
    async with MarvinClient(api_token="tok") as client:
        with pytest.raises(MarvinAuthError) as exc_info:
            await client.test_credentials()
    assert exc_info.value.status == 403


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


def test_marvin_auth_error_is_subclass_of_marvin_api_error():
    """MarvinAuthError is a subclass of MarvinAPIError."""
    err = MarvinAuthError("test", required_token="api")
    assert isinstance(err, MarvinAPIError)


@pytest.mark.asyncio
async def test_401_is_instance_of_marvin_api_error(mock_responses):
    """MarvinAuthError raised on 401 is also an instance of MarvinAPIError."""
    mock_responses.post(f"{BASE}/test", status=401)
    async with MarvinClient(api_token="tok") as client:
        with pytest.raises(MarvinAPIError) as exc_info:
            await client.test_credentials()
    assert isinstance(exc_info.value, MarvinAuthError)
