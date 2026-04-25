"""Shared pytest fixtures for py-amazing-marvin tests."""

from __future__ import annotations

import pytest
import pytest_asyncio
from aioresponses import aioresponses

from amazing_marvin.client import MarvinClient


@pytest.fixture
def mock_aioresponses():
    with aioresponses() as m:
        yield m


@pytest_asyncio.fixture
async def api_client():
    """MarvinClient with only api_token, using its own session."""
    async with MarvinClient(api_token="test-api-token") as client:
        yield client


@pytest_asyncio.fixture
async def full_client():
    """MarvinClient with both tokens."""
    async with MarvinClient(
        api_token="test-api-token",
        full_access_token="test-full-token",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def throttled_client():
    """MarvinClient with throttle=True."""
    async with MarvinClient(api_token="test-api-token", throttle=True) as client:
        yield client
