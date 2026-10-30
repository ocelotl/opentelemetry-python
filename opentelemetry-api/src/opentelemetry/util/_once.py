# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""One-shot execution primitive used to guard global provider initialisation.

This module provides :class:`Once`, which runs a callable the first time it is
asked to and ignores every later request. The API uses it to make sure a global
provider is set exactly once even when several threads race to set it.
"""

from collections.abc import Callable
from threading import Lock


class Once:
    """Execute a function exactly once and block all callers until the function returns

    Same as golang's `sync.Once <https://pkg.go.dev/sync#Once>`_
    """

    def __init__(self) -> None:
        """Initialize the lock and mark the guarded function as not yet executed."""
        self._lock = Lock()
        self._done = False

    def do_once(self, func: Callable[[], None]) -> bool:
        """Execute ``func`` if it hasn't been executed or return.

        Will block until ``func`` has been called by one thread.

        Args:
            func: The callable to execute. It takes no argument and its return
                value is discarded. It is called at most once over the lifetime
                of this :class:`Once` instance, no matter how many threads call
                this method.

        Returns:
            Whether or not ``func`` was executed in this call
        """

        # fast path, try to avoid locking
        if self._done:
            return False

        with self._lock:
            if not self._done:
                func()
                self._done = True
                return True
        return False
