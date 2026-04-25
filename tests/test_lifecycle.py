"""Tests for FR-003/004 — session ownership and no global state (T013)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from aioresponses import aioresponses
from yarl import URL

from amazing_marvin.client import MarvinClient
from amazing_marvin.exceptions import MarvinAPIError

BASE = "https://serv.amazingmarvin.com/api"


@pytest.fixture
def mock_responses():
    with aioresponses() as m:
        yield m


# ---------------------------------------------------------------------------
# Borrowed session — NOT closed after use
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_borrowed_session_not_closed_after_call(mock_responses):
    """When a session is passed in, it is NOT closed after the call."""
    mock_responses.get(f"{BASE}/todayItems", payload=[])

    async with aiohttp.ClientSession() as session:
        client = MarvinClient(api_token="tok", session=session)
        result = await client.get_today_items()
        # Session must still be open
        assert not session.closed
        assert result == []


@pytest.mark.asyncio
async def test_borrowed_session_owns_false(mock_responses):
    """Client with session= has _owns_session=False."""
    async with aiohttp.ClientSession() as session:
        client = MarvinClient(api_token="tok", session=session)
        assert client._owns_session is False


# ---------------------------------------------------------------------------
# Owned session — created on __aenter__, closed on __aexit__
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_owned_session_created_on_enter_closed_on_exit(mock_responses):
    """Owned session is created on __aenter__ and closed exactly once on __aexit__."""
    mock_responses.post(f"{BASE}/test", payload="OK")

    client = MarvinClient(api_token="tok")
    assert client._session is None  # no session before entering

    async with client:
        assert client._session is not None
        assert not client._session.closed
        await client.test_credentials()

    # After exiting, session should be None (closed)
    assert client._session is None


@pytest.mark.asyncio
async def test_owned_session_close_called_exactly_once():
    """__aexit__ closes the owned session exactly once."""
    mock_session = MagicMock(spec=aiohttp.ClientSession)
    mock_session.closed = False
    mock_session.close = AsyncMock()

    client = MarvinClient(api_token="tok")
    client._session = mock_session  # inject directly

    await client.__aexit__(None, None, None)
    mock_session.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# No session, no async with — raises MarvinAPIError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_without_session_raises_marvin_api_error(mock_responses):
    """Calling a method before entering context manager raises MarvinAPIError."""
    client = MarvinClient(api_token="tok")
    with pytest.raises(MarvinAPIError, match="no session"):
        await client.test_credentials()


# ---------------------------------------------------------------------------
# No global state — two clients with different tokens don't cross-contaminate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_clients_no_cross_contamination(mock_responses):
    """Two clients with different tokens each send their own token."""
    mock_responses.post(f"{BASE}/test", payload="OK")
    mock_responses.post(f"{BASE}/test", payload="OK")

    async with MarvinClient(api_token="token-A") as client_a:
        async with MarvinClient(api_token="token-B") as client_b:
            await client_a.test_credentials()
            await client_b.test_credentials()

    calls = list(mock_responses.requests.get(("POST", URL(f"{BASE}/test")), []))
    assert len(calls) == 2
    headers_seen = [c.kwargs.get("headers", {}).get("X-API-Token") for c in calls]
    assert set(headers_seen) == {"token-A", "token-B"}
