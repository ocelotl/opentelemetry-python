# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""``TestBase`` subclasses that drive an ASGI application through ``asgiref``.

An ASGI application is a coroutine taking a scope dict and a pair of ``receive``
and ``send`` callables, so a test has to build the scope, feed messages in and
collect messages out. ``asgiref.testing.ApplicationCommunicator`` does that
bookkeeping; the classes here hold one, supply a default HTTP scope and expose
the send and receive steps as methods.

Pick :class:`AsyncAsgiTestBase` for new tests: it inherits
``unittest.IsolatedAsyncioTestCase``, so its test methods are coroutines that
the runner awaits directly. :class:`AsgiTestBase` is the older form, whose test
methods are ordinary functions that drive the event loop themselves.
"""

import asyncio
from unittest import IsolatedAsyncioTestCase

from asgiref.testing import ApplicationCommunicator

from opentelemetry.test.test_base import TestBase


def setup_testing_defaults(scope):
    """Fill an ASGI scope with the fields of a plain ``GET /`` over HTTP.

    Named after ``wsgiref.util.setup_testing_defaults``, and like it, this
    updates the mapping in place and returns nothing. Keys the mapping already
    carries are overwritten, so set the fields a test cares about after calling
    this rather than before.

    Args:
        scope: The connection scope to fill. It gains ``client``, ``headers``,
            ``http_version``, ``method``, ``path``, ``query_string``,
            ``scheme``, ``server`` and ``type``. The defaults describe an
            HTTP/1.0 ``GET /`` from ``127.0.0.1`` with no headers and no query
            string. Fields an ASGI server would also set, ``asgi`` and
            ``root_path`` among them, are not added.
    """
    scope.update(
        {
            "client": ("127.0.0.1", 32767),
            "headers": [],
            "http_version": "1.0",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "scheme": "http",
            "server": ("127.0.0.1", 80),
            "type": "http",
        }
    )


class AsgiTestBase(TestBase):
    """Base class for a synchronous test that drives an ASGI application.

    Test methods are ordinary functions, and each call into the application
    runs the event loop to completion through
    ``asyncio.get_event_loop().run_until_complete``. Prefer
    :class:`AsyncAsgiTestBase` in new code, whose test methods are coroutines.

    Call ``seed_app`` with the application first, then ``send_input`` or
    ``send_default_request``, then ``get_output`` or ``get_all_output``.
    ``self.scope`` is the scope the application will see; edit it before
    ``seed_app``, because the communicator is given the scope at construction.

    ``tearDown`` waits for the application to finish but does not call
    ``TestBase.tearDown``, so the trace and metrics globals this class installed
    stay installed until the next ``setUp`` replaces them.
    """

    def setUp(self):
        """Install the in-memory pipelines and build a default HTTP scope.

        Leaves ``self.communicator`` as ``None``: there is no application until
        ``seed_app`` is called.
        """
        super().setUp()

        self.scope = {}
        setup_testing_defaults(self.scope)
        self.communicator = None

    def tearDown(self):
        """Wait for the seeded application to finish, if there is one.

        Waiting surfaces an exception the application raised after the last
        message a test read, which would otherwise be swallowed. This override
        does not call ``super().tearDown()``, so the trace and metrics globals
        are not reset here.
        """
        if self.communicator:
            asyncio.get_event_loop().run_until_complete(self.communicator.wait())

    def seed_app(self, app):
        """Attach an ASGI application to the scope built by ``setUp``.

        Call this once per test. Calling it again replaces the communicator and
        abandons the previous application without waiting for it.

        Args:
            app: The ASGI application to drive. It is instantiated against
                ``self.scope`` as it stands at this moment, so later edits to
                ``self.scope`` do not reach the application.
        """
        self.communicator = ApplicationCommunicator(app, self.scope)

    def send_input(self, message):
        """Send one ASGI message to the application and run the loop.

        Args:
            message: The message to deliver, for example
                ``{"type": "http.request", "body": b""}``. Its ``type`` has to
                be one the application expects for the scope type.
        """
        asyncio.get_event_loop().run_until_complete(self.communicator.send_input(message))

    def send_default_request(self):
        """Send an ``http.request`` message with an empty body.

        This is the one message a plain ``GET`` needs, since the absence of
        ``more_body`` tells the application the body is complete.
        """
        self.send_input({"type": "http.request", "body": b""})

    def get_output(self):
        """Take the next message the application sent.

        Returns:
            The next ASGI message, for example an ``http.response.start``.

        Raises:
            asyncio.TimeoutError: When no message is already queued. The wait
                is zero seconds, so this reads what the application has
                produced rather than waiting for it to produce more.
        """
        output = asyncio.get_event_loop().run_until_complete(self.communicator.receive_output(0))
        return output

    def get_all_output(self):
        """Take every message the application has already sent.

        Returns:
            A list of ASGI messages, in the order the application sent them,
            emptied out until nothing is queued. An application that has sent
            nothing yields an empty list rather than an error.
        """
        outputs = []
        while True:
            try:
                outputs.append(self.get_output())
            except asyncio.TimeoutError:
                break
        return outputs


class AsyncAsgiTestBase(TestBase, IsolatedAsyncioTestCase):
    """Base class for a test whose methods are coroutines.

    Same shape as :class:`AsgiTestBase`, but ``send_input``,
    ``send_default_request``, ``get_output`` and ``get_all_output`` are
    coroutines that a test method awaits, and ``IsolatedAsyncioTestCase`` runs
    each test method on its own event loop. Prefer this class in new code.

    ``tearDown`` has the same two limits as in :class:`AsgiTestBase`: it does
    not call ``TestBase.tearDown``, so the trace and metrics globals are not
    reset, and it drives its own loop rather than the one
    ``IsolatedAsyncioTestCase`` provides. Override ``asyncTearDown`` instead
    when a test needs cleanup that awaits.
    """

    def setUp(self):
        """Install the in-memory pipelines and build a default HTTP scope."""
        super().setUp()

        self.scope = {}
        setup_testing_defaults(self.scope)
        self.communicator = None

    def tearDown(self):
        """Wait for the seeded application to finish, if there is one.

        This override does not call ``super().tearDown()``, so the trace and
        metrics globals are not reset here.
        """
        if self.communicator:
            asyncio.get_event_loop().run_until_complete(self.communicator.wait())

    def seed_app(self, app):
        """Attach an ASGI application to the scope built by ``setUp``.

        Args:
            app: The ASGI application to drive. It is instantiated against
                ``self.scope`` as it stands at this moment, so later edits to
                ``self.scope`` do not reach the application.
        """
        self.communicator = ApplicationCommunicator(app, self.scope)

    async def send_input(self, message):
        """Send one ASGI message to the application.

        Args:
            message: The message to deliver, for example
                ``{"type": "http.request", "body": b""}``.
        """
        await self.communicator.send_input(message)

    async def send_default_request(self):
        """Send an ``http.request`` message with an empty body."""
        await self.send_input({"type": "http.request", "body": b""})

    async def get_output(self, timeout=0.01):
        """Wait for the next message the application sends.

        Args:
            timeout: Seconds to wait for a message before giving up.

        Returns:
            The next ASGI message.

        Raises:
            asyncio.TimeoutError: When no message arrives within ``timeout``.
        """
        return await self.communicator.receive_output(timeout)

    async def get_all_output(self, timeout=0.01):
        """Collect messages until the application stops sending them.

        Args:
            timeout: Seconds to wait for each further message. The call takes
                at least this long, because it ends by waiting for a message
                that never arrives.

        Returns:
            A list of ASGI messages in the order the application sent them.
            An application that sends nothing yields an empty list.
        """
        outputs = []
        while True:
            try:
                outputs.append(await self.communicator.receive_output(timeout))
            except asyncio.TimeoutError:
                break
        return outputs
