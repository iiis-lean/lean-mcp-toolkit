import asyncio

import pytest

from lean_mcp_toolkit.backends.lean_explore.base import run_async


def test_run_async_respects_timeout() -> None:
    async def _slow() -> int:
        await asyncio.sleep(0.05)
        return 1

    with pytest.raises(TimeoutError):
        run_async(_slow(), timeout_seconds=0.001)
