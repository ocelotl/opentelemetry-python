# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Conversion of SDK spans into the protobuf trace export request.

``encode_spans`` is the only name the OTLP exporters import from here, by way of
``opentelemetry.exporter.otlp.proto.common.trace_encoder``. Everything else is
private to this module.

The encoding regroups a flat sequence of spans into the two levels of nesting
the protocol requires, resource then instrumentation scope, and then converts
each span field by field.
"""

import logging
from collections import defaultdict
from collections.abc import Sequence

from opentelemetry.exporter.otlp.proto.common._internal import (
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_resource,
    _encode_span_id,
    _encode_trace_id,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest as PB2ExportTraceServiceRequest,
)
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ResourceSpans as PB2ResourceSpans,
)
from opentelemetry.proto.trace.v1.trace_pb2 import ScopeSpans as PB2ScopeSpans
from opentelemetry.proto.trace.v1.trace_pb2 import Span as PB2SPan
from opentelemetry.proto.trace.v1.trace_pb2 import SpanFlags as PB2SpanFlags
from opentelemetry.proto.trace.v1.trace_pb2 import Status as PB2Status
from opentelemetry.sdk.trace import Event, ReadableSpan
from opentelemetry.trace import Link, SpanKind
from opentelemetry.trace.span import SpanContext, Status, TraceState

# pylint: disable=E1101
_SPAN_KIND_MAP = {
    SpanKind.INTERNAL: PB2SPan.SpanKind.SPAN_KIND_INTERNAL,
    SpanKind.SERVER: PB2SPan.SpanKind.SPAN_KIND_SERVER,
    SpanKind.CLIENT: PB2SPan.SpanKind.SPAN_KIND_CLIENT,
    SpanKind.PRODUCER: PB2SPan.SpanKind.SPAN_KIND_PRODUCER,
    SpanKind.CONSUMER: PB2SPan.SpanKind.SPAN_KIND_CONSUMER,
}

_logger = logging.getLogger(__name__)


def encode_spans(
    sdk_spans: Sequence[ReadableSpan],
) -> PB2ExportTraceServiceRequest:
    """Encode finished spans as the protobuf request body of an OTLP trace export.

    Args:
        sdk_spans: The spans to export, in any order. They are grouped by
            resource and by instrumentation scope during encoding, so spans that
            share a resource and a scope end up in one ``ScopeSpans`` message
            whatever order they arrive in. An empty sequence produces a request
            with no ``resource_spans``, which the protocol allows.

    Returns:
        The ``ExportTraceServiceRequest`` to send over gRPC or, serialized, as
        the body of an HTTP request.

    Raises:
        KeyError: If the kind of any span is not one of the five
            :class:`opentelemetry.trace.SpanKind` members that ``_SPAN_KIND_MAP``
            covers, which includes the case of a span whose kind is ``None``.
            Nothing is exported in that case: the whole batch is lost, not only
            the one span.
    """
    return PB2ExportTraceServiceRequest(resource_spans=_encode_resource_spans(sdk_spans))


def _encode_resource_spans(
    sdk_spans: Sequence[ReadableSpan],
) -> list[PB2ResourceSpans]:
    """Group spans by resource and instrumentation scope and encode each group.

    Grouping uses the resource and the instrumentation scope as dictionary keys,
    so two spans share a group only when both compare equal. Spans with no
    instrumentation scope form a group of their own, whose ``ScopeSpans`` message
    carries an empty scope and no schema URL.

    Args:
        sdk_spans: The spans to group and encode.

    Returns:
        One ``ResourceSpans`` per distinct resource, each holding one
        ``ScopeSpans`` per distinct instrumentation scope found under that
        resource. The resources appear in the order their first span was seen.
    """
    # We need to inspect the spans and group + structure them as:
    #
    #   Resource
    #     Instrumentation Library
    #       Spans
    #
    # First loop organizes the SDK spans in this structure. Protobuf messages
    # are not hashable so we stick with SDK data in this phase.
    #
    # Second loop encodes the data into Protobuf format.
    #
    sdk_resource_spans = defaultdict(lambda: defaultdict(list))

    for sdk_span in sdk_spans:
        sdk_resource = sdk_span.resource
        sdk_instrumentation = sdk_span.instrumentation_scope or None
        pb2_span = _encode_span(sdk_span)

        sdk_resource_spans[sdk_resource][sdk_instrumentation].append(pb2_span)

    pb2_resource_spans = []

    for sdk_resource, sdk_instrumentations in sdk_resource_spans.items():
        scope_spans = []
        for sdk_instrumentation, pb2_spans in sdk_instrumentations.items():
            scope_spans.append(
                PB2ScopeSpans(
                    scope=(_encode_instrumentation_scope(sdk_instrumentation)),
                    spans=pb2_spans,
                    schema_url=sdk_instrumentation.schema_url if sdk_instrumentation else None,
                )
            )
        pb2_resource_spans.append(
            PB2ResourceSpans(
                resource=_encode_resource(sdk_resource),
                scope_spans=scope_spans,
                schema_url=sdk_resource.schema_url,
            )
        )

    return pb2_resource_spans


def _span_flags(parent_span_context: SpanContext | None) -> int:
    """Compute the ``flags`` field recording whether a parent or link is remote.

    The W3C trace flags occupy the low 8 bits of the field and are not set here.
    ``SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK`` is always set, which tells the
    receiver that the ``is_remote`` bit carries a real answer rather than
    "unknown".

    Args:
        parent_span_context: The span context of the parent, or of the linked
            span. ``None`` means there is no parent, and the ``is_remote`` bit is
            left clear.

    Returns:
        The bit mask to put in the ``flags`` field of a ``Span`` or of a
        ``Span.Link``.
    """
    flags = PB2SpanFlags.SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK
    if parent_span_context and parent_span_context.is_remote:
        flags |= PB2SpanFlags.SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK
    return flags


def _encode_span(sdk_span: ReadableSpan) -> PB2SPan:
    """Encode one span, without its resource or its instrumentation scope.

    The resource and the scope are carried by the enclosing ``ResourceSpans`` and
    ``ScopeSpans`` messages, so they are not repeated here. The three
    ``dropped_*_count`` fields report what the SDK's limits discarded while the
    span was recording, not anything this module discards.

    Args:
        sdk_span: A finished span. Its ``end_time`` is read directly, so a span
            that has not ended yet encodes ``end_time_unix_nano`` as 0.

    Returns:
        The protobuf ``Span``.

    Raises:
        KeyError: If the span kind is not one of the five
            :class:`opentelemetry.trace.SpanKind` members that ``_SPAN_KIND_MAP``
            covers, which includes the case of a span whose kind is ``None``.
    """
    span_context = sdk_span.get_span_context()
    return PB2SPan(
        trace_id=_encode_trace_id(span_context.trace_id),
        span_id=_encode_span_id(span_context.span_id),
        trace_state=_encode_trace_state(span_context.trace_state),
        parent_span_id=_encode_parent_id(sdk_span.parent),
        name=sdk_span.name,
        kind=_SPAN_KIND_MAP[sdk_span.kind],
        start_time_unix_nano=sdk_span.start_time,
        end_time_unix_nano=sdk_span.end_time,
        attributes=_encode_attributes(sdk_span.attributes),
        events=_encode_events(sdk_span.events),
        links=_encode_links(sdk_span.links),
        status=_encode_status(sdk_span.status),
        dropped_attributes_count=sdk_span.dropped_attributes,
        dropped_events_count=sdk_span.dropped_events,
        dropped_links_count=sdk_span.dropped_links,
        flags=_span_flags(sdk_span.parent),
    )


def _encode_events(
    events: Sequence[Event],
) -> list[PB2SPan.Event] | None:
    """Encode the events recorded on a span.

    Args:
        events: The events in the order the span recorded them.

    Returns:
        One ``Span.Event`` per event, or ``None`` when ``events`` is empty or
        ``None``. Passing ``None`` to the ``events`` field of a protobuf ``Span``
        leaves the field at its default, which is what an unset repeated field
        already is, so the two results are equivalent on the wire.
    """
    pb2_events = None
    if events:
        pb2_events = []
        for event in events:
            encoded_event = PB2SPan.Event(
                name=event.name,
                time_unix_nano=event.timestamp,
                attributes=_encode_attributes(event.attributes),
                dropped_attributes_count=event.dropped_attributes,
            )
            pb2_events.append(encoded_event)
    return pb2_events


def _encode_links(links: Sequence[Link]) -> Sequence[PB2SPan.Link]:
    """Encode the links recorded on a span.

    Each link carries its own ``flags``, computed from the span context of the
    linked span, so a link to a remote span is marked remote independently of the
    span that holds the link.

    Args:
        links: The links in the order the span recorded them.

    Returns:
        One ``Span.Link`` per link. When ``links`` is empty or ``None`` the
        result is ``None``, which the ``links`` field of a protobuf ``Span``
        accepts and treats as an unset repeated field.
    """
    pb2_links = None
    if links:
        pb2_links = []
        for link in links:
            encoded_link = PB2SPan.Link(
                trace_id=_encode_trace_id(link.context.trace_id),
                span_id=_encode_span_id(link.context.span_id),
                attributes=_encode_attributes(link.attributes),
                dropped_attributes_count=link.dropped_attributes,
                flags=_span_flags(link.context),
            )
            pb2_links.append(encoded_link)
    return pb2_links


def _encode_status(status: Status) -> PB2Status | None:
    """Encode the status of a span.

    Args:
        status: The status the SDK recorded. ``None`` means the span has no
            status at all, which is different from a status whose code is
            ``UNSET``.

    Returns:
        The protobuf ``Status`` with the numeric status code and the description,
        or ``None`` when ``status`` is ``None``. A description of ``None`` leaves
        the ``message`` field at the empty string.
    """
    pb2_status = None
    if status is not None:
        pb2_status = PB2Status(
            code=status.status_code.value,
            message=status.description,
        )
    return pb2_status


def _encode_trace_state(trace_state: TraceState) -> str | None:
    """Encode the W3C trace state as the single header string the protocol carries.

    Args:
        trace_state: The trace state from the span context. An empty trace state
            encodes as the empty string.

    Returns:
        The entries joined as ``key=value`` pairs separated by commas, in the
        order the trace state holds them, or ``None`` when ``trace_state`` is
        ``None``.
    """
    pb2_trace_state = None
    if trace_state is not None:
        pb2_trace_state = ",".join([f"{key}={value}" for key, value in (trace_state.items())])
    return pb2_trace_state


def _encode_parent_id(context: SpanContext | None) -> bytes | None:
    """Encode the span identifier of a parent span.

    Args:
        context: The span context of the parent. ``None`` means the span is a
            root span.

    Returns:
        The 8 bytes of the parent span identifier, or ``None`` for a root span,
        which leaves ``parent_span_id`` empty.
    """
    if context:
        return _encode_span_id(context.span_id)
    return None
