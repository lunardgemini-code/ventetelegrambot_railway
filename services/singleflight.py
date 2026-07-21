"""Coalesce concurrent asynchronous loads for the same in-process key."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Generic, Hashable, TypeVar


KeyT = TypeVar("KeyT", bound=Hashable)
ValueT = TypeVar("ValueT")


class AsyncSingleFlight(Generic[KeyT, ValueT]):
    """Share one loader task between concurrent callers with the same key."""

    def __init__(self) -> None:
        self._tasks: dict[KeyT, asyncio.Task[ValueT]] = {}

    async def run(
        self,
        key: KeyT,
        loader: Callable[[], Awaitable[ValueT]],
    ) -> ValueT:
        task = self._tasks.get(key)
        if task is None:
            task = asyncio.create_task(loader())
            self._tasks[key] = task

            def cleanup(done: asyncio.Task[ValueT]) -> None:
                if self._tasks.get(key) is done:
                    self._tasks.pop(key, None)

            task.add_done_callback(cleanup)
        return await asyncio.shield(task)

    def clear(self) -> None:
        """Forget tracked tasks without cancelling work already in progress."""
        self._tasks.clear()

    def __len__(self) -> int:
        return len(self._tasks)


__all__ = ["AsyncSingleFlight"]
