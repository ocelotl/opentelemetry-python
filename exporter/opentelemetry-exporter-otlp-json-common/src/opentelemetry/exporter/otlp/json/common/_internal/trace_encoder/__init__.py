# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pyright: reportCallIssue=false

"""Encoding of SDK spans into OTLP JSON trace messages.

``encode_spans`` is the entry point and is re-exported from
``opentelemetry.exporter.otlp.json.common.trace_encoder``, which is where a
span exporter should import it from. The rest of this module is private.

A span exporter hands over a flat collection of spans, while OTLP wants them
grouped first by resource and then by instrumentation scope. Rebuilding that
grouping is most of the work here, and it relies on both
``opentelemetry.sdk.resources.Resource`` and
``opentelemetry.sdk.util.instrumentation.InstrumentationScope`` being hashable,
so that each can be used as a dictionary key.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Collection

from opentelemetry.exporter.otlp.json.common._internal import (
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_resource,
    _encode_span_id,
    _encode_trace_id,
)
from opentelemetry.proto_json.collector.trace.v1.trace_service import (
    ExportTraceServiceRequest as JSONExportTraceServiceRequest,
)
from opentelemetry.proto_json.trace.v1.trace import (
    ResourceSpans as JSONResourceSpans,
)
from opentelemetry.proto_json.trace.v1.trace import (
    ScopeSpans as JSONScopeSpans,
)
from opentelemetry.proto_json.trace.v1.trace import Span as JSONSpan
from opentelemetry.proto_json.trace.v1.trace import (
    SpanFlags as JSONSpanFlags,
)
from opentelemetry.proto_json.trace.v1.trace import Status as JSONStatus
from opentelemetry.sdk.trace import Event, ReadableSpan
from opentelemetry.trace import Link, SpanKind
from opentelemetry.trace.span import SpanContext, Status, TraceState

# pylint: disable=E1101
_SPAN_KIND_MAP = {
    SpanKind.INTERNAL: JSONSpan.SpanKind.SPAN_KIND_INTERNAL,
    SpanKind.SERVER: JSONSpan.SpanKind.SPAN_KIND_SERVER,
    SpanKind.CLIENT: JSONSpan.SpanKind.SPAN_KIND_CLIENT,
    SpanKind.PRODUCER: JSONSpan.SpanKind.SPAN_KIND_PRODUCER,
    SpanKind.CONSUMER: JSONSpan.SpanKind.SPAN_KIND_CONSUMER,
}

_logger = logging.getLogger(__name__)


def encode_spans(
    sdk_spans: Collection[ReadableSpan],
) -> JSONExportTraceServiceRequest:
    """Encode a batch of SDK spans as an OTLP export request.

    Args:
        sdk_spans: the spans to export, in any order and from any number of
            resources and instrumentation scopes.

    Returns:
        An ``ExportTraceServiceRequest`` holding every span in ``sdk_spans``,
        regrouped by resource and then by instrumentation scope. An empty
        ``sdk_spans`` gives a request with no resource spans.

    Raises:
        KeyError: if the kind of one of the spans is not one of the five
            members of ``opentelemetry.trace.SpanKind``. One such span fails
            the export of the whole batch.
    """
    return JSONExportTraceServiceRequest(resource_spans=_encode_resource_spans(sdk_spans))


def _encode_resource_spans(
    sdk_spans: Collection[ReadableSpan],
) -> list[JSONResourceSpans]:
    """Group a flat collection of SDK spans into OTLP ``ResourceSpans``.

    Spans sharing a resource end up in one ``ResourceSpans``, and within it
    spans sharing an instrumentation scope end up in one ``ScopeSpans``. The
    schema URL of the resource is written on the ``ResourceSpans`` and the
    schema URL of the scope on the ``ScopeSpans``.

    Args:
        sdk_spans: the spans to group, in any order.

    Returns:
        One ``ResourceSpans`` per distinct resource, in the order each resource
        was first seen in ``sdk_spans``. A span whose instrumentation scope is
        absent or falsy is grouped under a scope of ``None``, which encodes as
        an empty scope message and leaves the schema URL of the ``ScopeSpans``
        unset.

    Raises:
        KeyError: if the kind of one of the spans is not one of the five
            members of ``opentelemetry.trace.SpanKind``.
    """
    sdk_resource_spans = defaultdict(lambda: defaultdict(list))

    for sdk_span in sdk_spans:
        sdk_resource = sdk_span.resource
        sdk_instrumentation = sdk_span.instrumentation_scope or None
        sdk_resource_spans[sdk_resource][sdk_instrumentation].append(_encode_span(sdk_span))

    json_resource_spans = []
    for sdk_resource, sdk_instrumentations in sdk_resource_spans.items():
        scope_spans = []
        for sdk_instrumentation, json_spans in sdk_instrumentations.items():
            scope_spans.append(
                JSONScopeSpans(
                    scope=(_encode_instrumentation_scope(sdk_instrumentation)),
                    spans=json_spans,
                    schema_url=sdk_instrumentation.schema_url if sdk_instrumentation else None,
                )
            )
        json_resource_spans.append(
            JSONResourceSpans(
                resource=_encode_resource(sdk_resource),
                scope_spans=scope_spans,
                schema_url=sdk_resource.schema_url,
            )
        )

    return json_resource_spans


def _span_flags(parent_span_context: SpanContext | None) -> int:
    """Build the OTLP ``flags`` field recording whether a span context was remote.

    ``SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK`` is always set, which tells a
    receiver that the ``is_remote`` bit beside it carries a real answer rather
    than meaning "unknown". ``SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK`` is set on top
    of it only for a context that came from a remote caller. The eight low bits
    that OTLP reserves for the W3C trace flags are left at zero.

    Both the ``flags`` of a span and the ``flags`` of a link are built here, so
    which span the answer is about depends on the caller. On a span it is the
    parent of that span, and on a link it is the span the link points at.

    Args:
        parent_span_context: the span context being asked about, which is the
            parent context of a span or the context a link points at. ``None``
            stands for a root span, and only a span reaches that case, since a
            link always carries a context.

    Returns:
        ``SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK`` on its own for a context that
        is not remote, and that mask combined with
        ``SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK`` for one that is. A
        ``parent_span_context`` of ``None`` and one with ``is_remote`` false
        give the same value, since both state that the context is known not to
        be remote.
    """
    flags = JSONSpanFlags.SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK
    if parent_span_context and parent_span_context.is_remote:
        flags |= JSONSpanFlags.SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK
    return int(flags)


def _encode_span(sdk_span: ReadableSpan) -> JSONSpan:
    """Encode one SDK span as an OTLP JSON ``Span``.

    Args:
        sdk_span: the span to encode. It is expected to have ended, since
            ``end_time`` is copied straight across and is ``None`` until then.

    Returns:
        The encoded ``Span``, including its events, its links, its status and
        the counts of attributes, events and links the SDK limits dropped. A
        span with no recorded span context encodes its trace and span
        identifiers as all-zero bytes.

    Raises:
        KeyError: if ``sdk_span.kind`` is not one of the five members of
            ``opentelemetry.trace.SpanKind``.
    """
    span_context = sdk_span.get_span_context()
    return JSONSpan(
        trace_id=_encode_trace_id(span_context.trace_id if span_context else 0),
        span_id=_encode_span_id(span_context.span_id if span_context else 0),
        trace_state=_encode_trace_state(span_context.trace_state if span_context else None),
        parent_span_id=_encode_context_span_id(sdk_span.parent),
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
    events: Collection[Event],
) -> list[JSONSpan.Event]:
    """Encode the events recorded on a span.

    Args:
        events: the events of one span, in the order the SDK recorded them.

    Returns:
        One ``Span.Event`` per event, carrying the name, the timestamp, the
        attributes and the count of attributes the SDK limits dropped from that
        event.
    """
    return [
        JSONSpan.Event(
            name=event.name,
            time_unix_nano=event.timestamp,
            attributes=_encode_attributes(event.attributes),
            dropped_attributes_count=event.dropped_attributes,
        )
        for event in events
    ]


def _encode_links(links: Collection[Link]) -> list[JSONSpan.Link]:
    """Encode the links recorded on a span.

    The trace state of a linked span context is not encoded, even though OTLP
    has a field for it.

    Args:
        links: the links of one span, in the order the SDK recorded them.

    Returns:
        One ``Span.Link`` per link, carrying the trace and span identifiers of
        the linked context, the attributes of the link, the count of attributes
        the SDK limits dropped from it, and the flags that record whether the
        linked context was remote.
    """
    return [
        JSONSpan.Link(
            trace_id=_encode_trace_id(link.context.trace_id),
            span_id=_encode_span_id(link.context.span_id),
            attributes=_encode_attributes(link.attributes),
            dropped_attributes_count=link.dropped_attributes,
            flags=_span_flags(link.context),
        )
        for link in links
    ]


def _encode_status(status: Status | None) -> JSONStatus | None:
    """Encode the status of a span.

    Args:
        status: the status the span ended with, or ``None`` when the span
            carries none.

    Returns:
        A ``Status`` whose code is the numeric value of the SDK status code and
        whose message is the description of the status, or ``None`` when
        ``status`` is ``None``, which leaves the field out of the encoded span.
    """
    return (
        JSONStatus(
            code=JSONStatus.StatusCode(status.status_code.value),
            message=status.description,
        )
        if status is not None
        else None
    )


def _encode_trace_state(trace_state: TraceState | None) -> str | None:
    """Encode a trace state as the single header string OTLP carries it in.

    Args:
        trace_state: the trace state of a span context, or ``None``.

    Returns:
        The entries rendered as ``key=value`` and joined with commas, in the
        order the trace state holds them, which W3C Trace Context defines as
        most recently updated first. An empty trace state gives an empty
        string, and a ``trace_state`` of ``None`` gives ``None``.
    """
    return ",".join([f"{key}={value}" for key, value in (trace_state.items())]) if trace_state is not None else None


def _encode_context_span_id(context: SpanContext | None) -> bytes | None:
    """Encode the span identifier held by a parent span context.

    Args:
        context: the span context of the parent of a span, or ``None`` for a
            root span.

    Returns:
        The eight-byte form of the span identifier, or ``None`` for a root
        span, which leaves ``parent_span_id`` out of the encoded span and so
        marks it as a root to the receiver.
    """
    return _encode_span_id(context.span_id) if context else None
