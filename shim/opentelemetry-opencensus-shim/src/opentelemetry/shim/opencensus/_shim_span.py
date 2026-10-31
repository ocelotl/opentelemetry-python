# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The OpenCensus span interface implemented over the OpenTelemetry tracing API.

``ShimSpan`` presents the method set of an OpenCensus span and records everything it is told on an
OpenTelemetry span. ``ShimTracer.start_span`` creates these and hands them back to OpenCensus
callers.

Two parts of the OpenCensus span interface are accepted and discarded with a warning: links and
span kind. The OpenCensus ``Tracer`` takes neither in ``start_span``, so the shim has neither to
hand to the OpenTelemetry tracer at the moment the OpenTelemetry span is created, and
OpenTelemetry fixes the kind of a span at creation. The incompatibility is listed in
https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/compatibility/opencensus.md#known-incompatibilities
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import wrapt
from opencensus.trace import execution_context
from opencensus.trace.blank_span import BlankSpan
from opencensus.trace.span import SpanKind
from opencensus.trace.status import Status
from opencensus.trace.time_event import MessageEvent

from opentelemetry import context, trace

if TYPE_CHECKING:
    from opentelemetry.shim.opencensus._shim_tracer import ShimTracer

_logger = logging.getLogger(__name__)

# Copied from Java
# https://github.com/open-telemetry/opentelemetry-java/blob/0d3a04669e51b33ea47b29399a7af00012d25ccb/opencensus-shim/src/main/java/io/opentelemetry/opencensusshim/SpanConverter.java#L24-L27
_MESSAGE_EVENT_ATTRIBUTE_KEY_TYPE = "message.event.type"
_MESSAGE_EVENT_ATTRIBUTE_KEY_SIZE_UNCOMPRESSED = "message.event.size.uncompressed"
_MESSAGE_EVENT_ATTRIBUTE_KEY_SIZE_COMPRESSED = "message.event.size.compressed"

_MESSAGE_EVENT_TYPE_STR_MAPPING = {
    0: "TYPE_UNSPECIFIED",
    1: "SENT",
    2: "RECEIVED",
}


def _opencensus_time_to_nanos(timestamp: str) -> int:
    """Converts an OpenCensus formatted time string (ISO 8601 with Z) to time.time_ns style
    unix timestamp

    ``datetime.strptime`` produces a naive datetime, and ``datetime.timestamp`` then reads a naive
    datetime as local time. OpenCensus writes these strings in UTC, so on a process whose local
    timezone is not UTC the result is displaced by the local UTC offset.

    Args:
        timestamp: An OpenCensus time string, as produced by
            ``opencensus.common.utils.to_iso_str``, for example ``2023-01-01T00:00:00.000000Z``.
            The fractional second part and the trailing ``Z`` are both required.

    Returns:
        The parsed time as a whole number of nanoseconds since the unix epoch, rounded, which is
        what the OpenTelemetry API takes for an event timestamp. It is displaced by the local UTC
        offset, as described above, so it names the intended instant only in a process whose local
        timezone is UTC.

    Raises:
        ValueError: When ``timestamp`` does not have that exact format.
    """
    # format taken from
    # https://github.com/census-instrumentation/opencensus-python/blob/c38c71b9285e71de94d0185ff3c5bf65ee163345/opencensus/common/utils/__init__.py#L76
    #
    # datetime.fromisoformat() does not work with the added "Z" until python 3.11
    seconds_float = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
    return round(seconds_float * 1e9)


# pylint: disable=abstract-method
class ShimSpan(wrapt.ObjectProxy):
    """The OpenCensus span interface, backed by an OpenTelemetry span.

    ``ShimTracer.start_span`` creates these and hands them to OpenCensus callers in place of an
    OpenCensus span. The methods that record data are overridden here and reach the OpenTelemetry
    span. Being a ``wrapt.ObjectProxy``, everything else is handled by the wrapped OpenCensus
    ``BlankSpan``, whose methods do nothing, so an unsupported OpenCensus call is silently
    accepted rather than raising ``AttributeError``.

    Two OpenCensus span members that are read by instrumentations, although they are not part of
    the documented OpenCensus ``BaseSpan`` interface, are set from the OpenTelemetry span at
    construction so they do not report the values the ``BlankSpan`` made up for itself:
    ``span_id`` is the span ID of the OpenTelemetry span as an integer, and
    ``same_process_as_parent_span`` is read from the span context of that same OpenTelemetry span
    rather than from its parent. A span context an OpenTelemetry tracer builds for a span it is
    creating is never remote, so ``same_process_as_parent_span`` is ``True`` on every shim span,
    including one whose parent was extracted from an incoming request.

    Args:
        wrapped: The OpenCensus ``BlankSpan`` to proxy.
        otel_span: The OpenTelemetry span that records everything this span is told.
        shim_tracer: The shim tracer that created this span. It starts the child spans and
            supplies the span to restore as current when this span is exited.
    """

    def __init__(
        self,
        wrapped: BlankSpan,
        *,
        otel_span: trace.Span,
        shim_tracer: "ShimTracer",
    ) -> None:
        """The parameters are documented on the class docstring."""
        super().__init__(wrapped)
        self._self_otel_span = otel_span
        self._self_shim_tracer = shim_tracer
        self._self_token: object = None

        # Set a few values for BlankSpan members (they appear to be part of the "public" API
        # even though they are not documented in BaseSpan). Some instrumentations may use these
        # and not expect an AttributeError to be raised. Set values from OTel where possible
        # and let ObjectProxy defer to the wrapped BlankSpan otherwise.
        sc = self._self_otel_span.get_span_context()
        self.same_process_as_parent_span = not sc.is_remote
        self.span_id = sc.span_id

    def span(self, name="child_span"):
        """Start a child span through the shim tracer and make it current.

        OpenCensus ``BlankSpan.span`` returns a child that is not attached to any context. This
        override goes through ``ShimTracer.start_span`` instead, so the returned span is attached.
        The parent of the child is therefore the span current in the OpenTelemetry context, which
        is this span only while this span is still the current one.

        Args:
            name: The name given to the child span.

        Returns:
            The started child shim span.
        """
        return self._self_shim_tracer.start_span(name=name)

    def add_attribute(self, attribute_key, attribute_value):
        """Set an attribute on the OpenTelemetry span.

        Args:
            attribute_key: The name of the attribute.
            attribute_value: The value of the attribute. Nothing is converted here, so an
                OpenTelemetry SDK span is what cleans it. A value that is not a ``bool``, ``str``,
                ``None``, ``bytes``, ``int``, ``float``, or a mapping or sequence of those, is
                logged as a warning and then passed through ``str``, or replaced by ``None`` when
                its type defines neither ``__str__`` nor ``__repr__``. The attribute key survives
                either way, so a bad value shows up on the span rather than disappearing from it.
                A non-recording span, which is what the shim holds while no OpenTelemetry tracer
                provider has been set, drops the attribute with no warning at all.
        """
        self._self_otel_span.set_attribute(attribute_key, attribute_value)

    def add_annotation(self, description, **attrs):
        """Record an OpenCensus annotation as an OpenTelemetry span event.

        The event is timestamped by the OpenTelemetry span at the moment of this call, because the
        OpenCensus annotation API carries no time of its own here.

        Args:
            description: The text of the annotation, which becomes the name of the event.
            **attrs: The attributes of the annotation, which become the attributes of the event.
        """
        self._self_otel_span.add_event(description, attrs)

    def add_message_event(self, message_event: MessageEvent):
        """Record an OpenCensus message event as an OpenTelemetry span event.

        The name of the event is the string form of ``message_event.id``. Its timestamp comes from
        ``message_event.timestamp`` through ``_opencensus_time_to_nanos``, so it is displaced by
        the local UTC offset exactly as that function documents, and it matches the instant the
        message event carries only on a process whose timezone is UTC. The type and the two sizes
        become the attributes
        ``message.event.type``, ``message.event.size.uncompressed`` and
        ``message.event.size.compressed``, the names the OpenCensus shim of opentelemetry-java
        uses. A size that is ``None`` contributes no attribute. The type attribute is the name of
        the OpenCensus type rather than its number, so ``TYPE_UNSPECIFIED``, ``SENT`` or
        ``RECEIVED``.

        Args:
            message_event: The OpenCensus ``MessageEvent`` to record.

        Raises:
            KeyError: When ``message_event.type`` is not one of the three values of
                ``opencensus.trace.time_event.Type``.
            ValueError: When ``message_event.timestamp`` is not an OpenCensus time string.
        """
        attrs = {
            _MESSAGE_EVENT_ATTRIBUTE_KEY_TYPE: _MESSAGE_EVENT_TYPE_STR_MAPPING[message_event.type],
        }
        if message_event.uncompressed_size_bytes is not None:
            attrs[_MESSAGE_EVENT_ATTRIBUTE_KEY_SIZE_UNCOMPRESSED] = message_event.uncompressed_size_bytes
        if message_event.compressed_size_bytes is not None:
            attrs[_MESSAGE_EVENT_ATTRIBUTE_KEY_SIZE_COMPRESSED] = message_event.compressed_size_bytes

        timestamp = _opencensus_time_to_nanos(message_event.timestamp)
        self._self_otel_span.add_event(
            str(message_event.id),
            attrs,
            timestamp=timestamp,
        )

    # pylint: disable=no-self-use
    def add_link(self, link):
        """Log a warning and discard the link.

        span links do not work with the shim because the OpenCensus Tracer does not accept
        links in start_span(). Same issue applies to SpanKind. Also see:
        https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/compatibility/opencensus.md#known-incompatibilities

        Args:
            link: The OpenCensus ``Link`` the caller wants to add. It is discarded, so the
                OpenTelemetry span is exported with no links at all.
        """
        _logger.warning("OpenTelemetry does not support links added after a span is created.")

    @property
    def span_kind(self):
        """Report the OpenCensus span kind of this span, which is always ``UNSPECIFIED``.

        Setting span_kind does not work with the shim because the OpenCensus Tracer does not
        accept the param in start_span() and there's no way to set OTel span kind after
        start_span().

        Returns:
            Always ``opencensus.trace.span.SpanKind.UNSPECIFIED``, whatever kind the OpenTelemetry
            span underneath has.
        """
        return SpanKind.UNSPECIFIED

    @span_kind.setter
    def span_kind(self, value):
        """Log a warning and discard the span kind.

        OpenTelemetry fixes the kind of a span when the span starts, and the OpenCensus ``Tracer``
        offers no way to pass one to ``start_span``, so every span the shim creates keeps the
        OpenTelemetry default kind of ``INTERNAL``.

        Args:
            value: The OpenCensus ``SpanKind`` the caller wants to set. It is discarded, and a
                later read of ``span_kind`` still reports ``UNSPECIFIED``.
        """
        _logger.warning("OpenTelemetry does not support setting span kind after a span is created.")

    def set_status(self, status: Status):
        """Set the status of the OpenTelemetry span from an OpenCensus status.

        An OpenCensus status carries a gRPC code, of which there are many, while an OpenTelemetry
        status is one of ``UNSET``, ``OK`` and ``ERROR``. Every OpenCensus code other than ``OK``
        becomes ``ERROR``, so the particular code does not survive the translation.

        The description is passed on, but OpenTelemetry keeps a description only on an ``ERROR``
        status, so a description accompanying an ``OK`` OpenCensus status is dropped, with a
        warning from the OpenTelemetry API. A non-recording span, which is what the shim holds
        while no OpenTelemetry tracer provider has been set, drops the whole status with no
        warning at all.

        Args:
            status: The OpenCensus ``Status`` to translate. Its ``is_ok`` property chooses between
                ``OK`` and ``ERROR``, and its ``description`` property supplies the description.
        """
        self._self_otel_span.set_status(
            trace.StatusCode.OK if status.is_ok else trace.StatusCode.ERROR,
            status.description,
        )

    def finish(self):
        """End the OpenTelemetry span, which is what hands an SDK span to its span processors.

        Note this method does not pop the span from current context. Use the OpenCensus
        Tracer.end_span() or a `with span: ...` statement (contextmanager) to do that.
        """
        self._self_otel_span.end()

    def __enter__(self):
        """Enter the context manager of the OpenTelemetry span and return this shim span.

        Returns:
            This shim span, so that ``with tracer.span() as span:`` binds the OpenCensus facing
            object rather than the OpenTelemetry span underneath it.
        """
        self._self_otel_span.__enter__()
        return self

    # pylint: disable=arguments-differ
    def __exit__(self, exception_type, exception_value, traceback):
        """End the OpenTelemetry span and restore the context from before the span was started.

        Ending goes through the context manager of the OpenTelemetry span rather than through
        ``finish``, so an exception leaving the block reaches the span: an SDK span that is still
        recording records it as an event and sets its own status to ``ERROR``. An ``ERROR`` is
        rejected on a span that already carries an ``OK`` status, so a caller that set an ``OK``
        status inside the block keeps that status and still gets the event. A caller that called
        ``finish`` inside the block gets neither, because the span has stopped recording by then.
        OpenCensus ``Span.__exit__`` would end the span through
        ``Tracer.end_span``, which here would end the OpenTelemetry span a second time, so this
        method does the context teardown itself instead.

        Args:
            exception_type: The class of the exception leaving the block, or ``None`` when the
                block completed normally.
            exception_value: The exception leaving the block, or ``None``.
            traceback: The traceback of that exception, or ``None``.
        """
        self._self_otel_span.__exit__(exception_type, exception_value, traceback)
        # OpenCensus Span.__exit__() calls Tracer.end_span()
        # https://github.com/census-instrumentation/opencensus-python/blob/2e08df591b507612b3968be8c2538dedbf8fab37/opencensus/trace/span.py#L390
        # but that would cause the OTel span to be ended twice. Instead, this code just copies
        # the context teardown from that method.
        context.detach(self._self_token)
        execution_context.set_current_span(self._self_shim_tracer.current_span())
