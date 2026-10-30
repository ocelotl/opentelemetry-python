# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Zipkin Export Encoder for Protobuf

API spec: https://github.com/openzipkin/zipkin-api/blob/master/zipkin.proto
"""

from collections.abc import Sequence

from opentelemetry.exporter.zipkin.encoder import Encoder
from opentelemetry.exporter.zipkin.node_endpoint import NodeEndpoint
from opentelemetry.exporter.zipkin.proto.http.v2.gen import zipkin_pb2
from opentelemetry.sdk.trace import Event
from opentelemetry.trace import Span, SpanKind


class ProtobufEncoder(Encoder):
    """Zipkin Export Encoder for Protobuf

    API spec: https://github.com/openzipkin/zipkin-api/blob/master/zipkin.proto

    Turns a batch of ended OpenTelemetry spans into the serialized bytes of a
    Zipkin ``ListOfSpans`` message, which ``ZipkinExporter`` sends as the body
    of one HTTP request. The encoder holds no state beyond the
    ``max_tag_value_length`` it inherits from its base class, so one instance
    serializes any number of batches.

    ``SPAN_KIND_MAP`` gives the Zipkin kind for each OpenTelemetry span kind.
    ``SpanKind.INTERNAL`` maps to the unspecified Zipkin kind, because Zipkin
    names only the four kinds that describe a remote relationship.
    """

    SPAN_KIND_MAP = {
        SpanKind.INTERNAL: zipkin_pb2.Span.Kind.SPAN_KIND_UNSPECIFIED,
        SpanKind.SERVER: zipkin_pb2.Span.Kind.SERVER,
        SpanKind.CLIENT: zipkin_pb2.Span.Kind.CLIENT,
        SpanKind.PRODUCER: zipkin_pb2.Span.Kind.PRODUCER,
        SpanKind.CONSUMER: zipkin_pb2.Span.Kind.CONSUMER,
    }

    @staticmethod
    def content_type():
        """Media type the exporter sets on the HTTP request that carries the batch.

        Returns:
            ``"application/x-protobuf"``, the media type Zipkin expects for a
            protobuf-encoded ``ListOfSpans``.
        """
        return "application/x-protobuf"

    def serialize(self, spans: Sequence[Span], local_endpoint: NodeEndpoint) -> bytes:
        """Encode a batch of spans as one serialized Zipkin ``ListOfSpans``.

        Every span of the batch is given the same encoded local endpoint, so one
        call describes the spans of a single node.

        Args:
            spans: The ended spans to encode, in the order they are to appear in
                the message. An empty sequence yields the serialization of an
                empty ``ListOfSpans``, which is an empty byte string.
            local_endpoint: Network context of the node that produced the spans.
                Its service name, IPv4 address, IPv6 address and port are copied
                into the ``local_endpoint`` field of every encoded span. The
                service name is always written; whichever of the IPv4 address,
                the IPv6 address and the port is ``None`` is left out.

        Returns:
            The protobuf wire-format bytes of the ``ListOfSpans`` message, ready
            to be used as an HTTP request body.
        """
        encoded_local_endpoint = self._encode_local_endpoint(local_endpoint)
        # pylint: disable=no-member
        encoded_spans = zipkin_pb2.ListOfSpans()
        for span in spans:
            encoded_spans.spans.append(self._encode_span(span, encoded_local_endpoint))
        return encoded_spans.SerializeToString()

    def _encode_span(self, span: Span, encoded_local_endpoint: zipkin_pb2.Endpoint) -> zipkin_pb2.Span:
        """Encode one span as a Zipkin ``Span`` message.

        Timestamps are converted from the nanoseconds the SDK records to the
        microseconds Zipkin stores, rounded to the nearest microsecond. The
        duration is the difference between the end and start times of the span,
        which means a span that has not ended raises ``TypeError`` here.

        The OpenTelemetry specification asks that a Zipkin field which can be
        absent be left out of the payload when it is empty in the OpenTelemetry
        span, so the tags, annotations, debug flag and parent identifier are
        each set only when they have a value. A span whose kind is ``SpanKind.INTERNAL``
        is encoded with the unspecified Zipkin kind, since Zipkin has no
        equivalent of an internal span.

        Args:
            span: The ended span to encode.
            encoded_local_endpoint: Already encoded local endpoint, shared by
                every span of the batch.

        Returns:
            The ``Span`` message, not yet serialized.
        """
        context = span.get_span_context()
        # pylint: disable=no-member
        encoded_span = zipkin_pb2.Span(
            trace_id=self._encode_trace_id(context.trace_id),
            id=self._encode_span_id(context.span_id),
            name=span.name,
            timestamp=self._nsec_to_usec_round(span.start_time),
            duration=self._nsec_to_usec_round(span.end_time - span.start_time),
            local_endpoint=encoded_local_endpoint,
            kind=self.SPAN_KIND_MAP[span.kind],
        )

        tags = self._extract_tags_from_span(span)
        if tags:
            encoded_span.tags.update(tags)

        annotations = self._encode_annotations(span.events)
        if annotations:
            encoded_span.annotations.extend(annotations)

        debug = self._encode_debug(context)
        if debug:
            encoded_span.debug = debug

        parent_id = self._get_parent_id(span.parent)
        if parent_id is not None:
            encoded_span.parent_id = self._encode_span_id(parent_id)

        return encoded_span

    def _encode_annotations(self, span_events: list[Event] | None) -> list | None:
        """Encode the events of a span as Zipkin ``Annotation`` messages.

        Each event becomes one annotation whose value is a JSON object mapping
        the event name to its attributes, and whose timestamp is the event time
        in microseconds. String attribute values are truncated to
        ``max_tag_value_length`` only when that limit is a positive number, and
        ``ZipkinExporter`` leaves it unset, so by default nothing is truncated.

        Args:
            span_events: The events recorded on the span, in the order they were
                added.

        Returns:
            One ``Annotation`` message per event, or ``None`` when the span
            recorded no events, so that the caller can leave the repeated field
            out of the encoded span.
        """
        annotations = self._extract_annotations_from_events(span_events)
        if annotations is None:
            encoded_annotations = None
        else:
            encoded_annotations = []
            for annotation in annotations:
                encoded_annotations.append(
                    zipkin_pb2.Annotation(
                        timestamp=annotation["timestamp"],
                        value=annotation["value"],
                    )
                )
        return encoded_annotations

    @staticmethod
    def _encode_local_endpoint(
        local_endpoint: NodeEndpoint,
    ) -> zipkin_pb2.Endpoint:
        """Encode the network context of the local node as an ``Endpoint`` message.

        The IPv4 and IPv6 addresses are written in their packed binary form,
        four and sixteen bytes respectively, which is what the Zipkin protobuf
        schema expects. An address or port that is ``None`` is left out of the
        message rather than written as a zero value.

        Args:
            local_endpoint: Network context of the node that produced the spans.

        Returns:
            The ``Endpoint`` message to attach to every span of the batch.
        """
        encoded_local_endpoint = zipkin_pb2.Endpoint(
            service_name=local_endpoint.service_name,
        )
        if local_endpoint.ipv4 is not None:
            encoded_local_endpoint.ipv4 = local_endpoint.ipv4.packed
        if local_endpoint.ipv6 is not None:
            encoded_local_endpoint.ipv6 = local_endpoint.ipv6.packed
        if local_endpoint.port is not None:
            encoded_local_endpoint.port = local_endpoint.port
        return encoded_local_endpoint

    @staticmethod
    def _encode_span_id(span_id: int) -> bytes:
        """Encode a span identifier for the protobuf transport.

        The JSON transport writes identifiers as hexadecimal strings; the
        protobuf schema takes the raw bytes instead.

        Args:
            span_id: The 64 bit span identifier.

        Returns:
            The identifier as 8 bytes, most significant byte first. A value that
            does not fit in 8 unsigned bytes raises ``OverflowError``.
        """
        return span_id.to_bytes(length=8, byteorder="big", signed=False)

    @staticmethod
    def _encode_trace_id(trace_id: int) -> bytes:
        """Encode a trace identifier for the protobuf transport.

        The JSON transport writes identifiers as hexadecimal strings; the
        protobuf schema takes the raw bytes instead.

        Args:
            trace_id: The 128 bit trace identifier.

        Returns:
            The identifier as 16 bytes, most significant byte first. A value
            that does not fit in 16 unsigned bytes raises ``OverflowError``.
        """
        return trace_id.to_bytes(length=16, byteorder="big", signed=False)
