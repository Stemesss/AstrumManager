# -*- coding: utf-8 -*-
"""Pytest configuration and shared fixtures."""
import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def reset_asyncio_backend():
    """Reset asyncio backend between tests."""
    pass
