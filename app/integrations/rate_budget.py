"""Bounded rolling request budgets shared by the one provider client."""

import threading
import time
from collections import deque
from collections.abc import Callable


class RateBudget:
    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._clock, self._sleep = clock, sleep
        self._global: deque[float] = deque(maxlen=20)
        self._endpoints: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def acquire(self, path: str) -> None:
        pieces = path.strip("/").split("/")
        # Group IDs into their API resource rather than giving each object a
        # fresh allowance. Resource-wide grouping is intentionally conservative.
        endpoint = "/".join(pieces[:2] if pieces[0] == "fx" else pieces[:1])
        with self._lock:
            now = self._clock()
            slots = self._endpoints.setdefault(endpoint, deque(maxlen=10))
            ready = max(
                now,
                self._global[0] + 1 if len(self._global) == 20 else now,
                slots[0] + 1 if len(slots) == 10 else now,
            )
            self._global.append(ready)
            slots.append(ready)
        if ready > now:
            self._sleep(ready - now)
