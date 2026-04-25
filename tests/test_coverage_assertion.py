"""SC-002 — endpoint coverage assertion and exception importability (T040)."""

from __future__ import annotations

import inspect

import pytest

from amazing_marvin.client import MarvinClient


def test_public_method_count_at_least_34():
    """MarvinClient has at least 34 public methods (regression guard)."""
    public_methods = [
        name
        for name, member in inspect.getmembers(MarvinClient, predicate=inspect.isfunction)
        if not name.startswith("_")
    ]
    count = len(public_methods)
    assert count >= 34, (
        f"Expected at least 34 public methods on MarvinClient, found {count}: {sorted(public_methods)}"
    )


def test_all_exception_classes_importable_from_amazing_marvin():
    """All 4 exception classes are importable directly from amazing_marvin."""
    from amazing_marvin import (
        MarvinAPIError,
        MarvinAuthError,
        MarvinNotFoundError,
        MarvinRateLimitError,
    )

    # Verify they are proper exception classes
    assert issubclass(MarvinAPIError, Exception)
    assert issubclass(MarvinAuthError, MarvinAPIError)
    assert issubclass(MarvinNotFoundError, MarvinAPIError)
    assert issubclass(MarvinRateLimitError, MarvinAPIError)
