# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Zipkin Exporter Transport Encoder

Base module and abstract class for concrete transport encoders to extend.
"""

import abc
import json
import logging
from collections.abc import Sequence
from enum import Enum
from typing import Any, TypeVar

from opentelemetry.exporter.zipkin.node_endpoint import NodeEndpoint
from opentelemetry.sdk.trace import Event
from opentelemetry.trace import (
    Span,
    SpanContext,
    StatusCode,
    format_span_id,
    format_trace_id,
)

EncodedLocalEndpointT = TypeVar("EncodedLocalEndpointT")

DEFAULT_MAX_TAG_VALUE_LENGTH = 128
NAME_KEY = "otel.library.name"
VERSION_KEY = "otel.library.version"
_SCOPE_NAME_KEY = "otel.scope.name"
_SCOPE_VERSION_KEY = "otel.scope.version"

logger = logging.getLogger(__name__)


class Protocol(Enum):
    """Enum of supported protocol formats.

    Values are human-readable strings so that they can be easily used by the
    OS environ var OTEL_EXPORTER_ZIPKIN_PROTOCOL (reserved for future usage).
    """

    V1 = "v1"
    V2 = "v2"


# pylint: disable=W0223
class Encoder(abc.ABC):
    """Base class for encoders that are used by the exporter.

    Args:
        max_tag_value_length: maximum length of an exported tag value. Values
          will be truncated to conform. Since values are serialized to a JSON
          list string, max_tag_value_length is honored at the element boundary.
    """

    def __init__(self, max_tag_value_length: int = DEFAULT_MAX_TAG_VALUE_LENGTH):
        """Initialize the encoder.

        The parameters are documented on the class.
        """
        self.max_tag_value_length = max_tag_value_length

    @staticmethod
    @abc.abstractmethod
    def content_type() -> str:
        """Return the media type of the payload this encoder produces.

        The exporter sends the value as the ``Content-Type`` header of every
        request to the Zipkin collector, so it has to name the format the
        collector should parse the body as.

        Returns:
            The media type, for example ``"application/json"``.
        """

    @abc.abstractmethod
    def serialize(self, spans: Sequence[Span], local_endpoint: NodeEndpoint) -> str:
        """Encode a batch of spans into a single request body.

        Args:
            spans: The spans to encode. An empty sequence still produces a
                valid body, which encodes to an empty list of spans.
            local_endpoint: The network context to attach to the encoded
                spans. Where it ends up in the payload depends on the Zipkin
                API version: v2 writes it once per span, v1 repeats it inside
                every annotation and every binary annotation.

        Returns:
            The request body to send to the Zipkin collector.
        """

    @abc.abstractmethod
    def _encode_span(self, span: Span, encoded_local_endpoint: EncodedLocalEndpointT) -> Any:
        """Encode one span.

        Per spec Zipkin fields that can be absent SHOULD be omitted from the
        payload when they are empty in the OpenTelemetry Span.

        https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/trace/sdk_exporters/zipkin.md#request-payload

        Args:
            span: The span to encode. It must have ended, because the encoding
                reads ``end_time`` to compute the duration.
            encoded_local_endpoint: The already encoded local endpoint, as
                returned by ``_encode_local_endpoint``. It is encoded once per
                batch and passed in here so that it is not rebuilt per span.

        Returns:
            The encoded span, in whatever representation the concrete encoder
            serializes, which for the JSON encoders is a ``dict``.
        """

    @staticmethod
    @abc.abstractmethod
    def _encode_local_endpoint(
        local_endpoint: NodeEndpoint,
    ) -> EncodedLocalEndpointT:
        """Encode the local endpoint once, for reuse across a whole batch.

        Args:
            local_endpoint: The network context of the node that recorded the
                spans.

        Returns:
            The encoded endpoint, to be handed to ``_encode_span`` for every
            span of the batch.
        """

    @staticmethod
    def _encode_debug(span_context) -> Any:
        """Report whether the span should carry the Zipkin ``debug`` flag.

        The sampled flag of the span context is used as the debug flag.
        OpenTelemetry has no separate debug flag to map onto it.

        Args:
            span_context: The span context to read the trace flags from.

        Returns:
            True when the context is sampled, which makes the caller emit a
            ``debug`` field. The encoders omit the field when this is false.
        """
        return span_context.trace_flags.sampled

    @staticmethod
    @abc.abstractmethod
    def _encode_span_id(span_id: int) -> Any:
        """Encode a span id into the representation the payload uses.

        Args:
            span_id: The span id, as the 64 bit integer the SDK holds.

        Returns:
            The encoded span id, which for the JSON encoders is the 16
            character lowercase hexadecimal string Zipkin expects.
        """

    @staticmethod
    @abc.abstractmethod
    def _encode_trace_id(trace_id: int) -> Any:
        """Encode a trace id into the representation the payload uses.

        Args:
            trace_id: The trace id, as the 128 bit integer the SDK holds.

        Returns:
            The encoded trace id, which for the JSON encoders is the 32
            character lowercase hexadecimal string Zipkin expects.
        """

    @staticmethod
    def _get_parent_id(span_context) -> int | None:
        """Extract the id of the parent span from whatever ``span.parent`` holds.

        ``span.parent`` is a ``SpanContext`` for an ordinary child span and
        ``None`` for a root span, and this also accepts a ``Span``, in which
        case the id is read from the parent of that span.

        Args:
            span_context: The value of ``span.parent``, or any other value,
                since anything that is neither a ``Span`` nor a
                ``SpanContext`` is treated as absent.

        Returns:
            The parent span id, or ``None`` when the argument is neither a
            ``Span`` nor a ``SpanContext``, which is what ``span.parent``
            holds for a root span. The encoders omit the ``parentId`` field
            when this is ``None``.

        Raises:
            AttributeError: If the argument is a ``Span`` whose ``parent`` is
                ``None``, since that branch reads ``span.parent.span_id``
                without guarding. Both encoders pass ``span.parent`` rather
                than the span, so they never reach this.
        """
        if isinstance(span_context, Span):
            parent_id = span_context.parent.span_id
        elif isinstance(span_context, SpanContext):
            parent_id = span_context.span_id
        else:
            parent_id = None
        return parent_id

    def _extract_tags_from_dict(self, tags_dict: dict | None) -> dict[str, str]:
        """Convert a mapping of attributes into Zipkin tags.

        Zipkin tag values are strings, so every value is stringified: a bool
        becomes ``"true"`` or ``"false"``, a number becomes its ``str``, and a
        sequence becomes a compact JSON array. A value of any other type, and
        a sequence when ``max_tag_value_length`` is 1, is dropped with a
        warning on the ``opentelemetry.exporter.zipkin.encoder`` logger rather
        than failing the export. A sequence whose elements do not fit the
        limit is not dropped: it is kept as the empty array ``"[]"``.

        Values are truncated to ``max_tag_value_length`` characters when that
        limit is set to a positive number. Truncation applies to the rendered
        string, so a truncated JSON array is not valid JSON on its own.

        Args:
            tags_dict: The attributes to convert, or ``None``. ``None`` and an
                empty mapping both yield an empty result.

        Returns:
            The tags, keyed by attribute name. Keys whose values could not be
            serialized are absent.
        """
        tags = {}
        if not tags_dict:
            return tags
        for attribute_key, attribute_value in tags_dict.items():
            if isinstance(attribute_value, bool):
                value = str(attribute_value).lower()
            elif isinstance(attribute_value, (int, float, str)):
                value = str(attribute_value)
            elif isinstance(attribute_value, Sequence):
                value = self._extract_tag_value_string_from_sequence(attribute_value)
                if not value:
                    logger.warning("Could not serialize tag %s", attribute_key)
                    continue
            else:
                logger.warning("Could not serialize tag %s", attribute_key)
                continue

            if self.max_tag_value_length is not None and self.max_tag_value_length > 0:
                value = value[: self.max_tag_value_length]
            tags[attribute_key] = value
        return tags

    def _extract_tag_value_string_from_sequence(self, sequence: Sequence):
        """Render a sequence attribute as a compact JSON array string.

        The length limit is honored at the element boundary rather than by
        cutting the finished string, so the result stays valid JSON. Elements
        are appended while the running length of the rendered array, counting
        the brackets, the quotes and the separating commas, stays within
        ``max_tag_value_length``. The first element that would exceed it ends
        the array, and the remaining elements are dropped silently.

        That running length measures each element before ``json.dumps``
        escapes it, so an element holding a non-ASCII character, a double
        quote or a backslash renders longer than it was counted as, and the
        array can come back longer than ``max_tag_value_length``. The caller
        then truncates it, which is the one case in which a sequence tag ends
        up as invalid JSON.

        An element that is not a bool, a number, a string or ``None`` is
        skipped without ending the array, and without counting towards the
        length.

        Args:
            sequence: The attribute value to render.

        Returns:
            The JSON array, or ``None`` when ``max_tag_value_length`` is 1,
            since one character cannot hold even an empty array. The caller
            treats ``None`` as a failure to serialize and drops the tag with a
            warning. A sequence whose elements all exceed the limit still
            returns ``"[]"``, which the caller keeps.
        """
        if self.max_tag_value_length and self.max_tag_value_length == 1:
            return None

        tag_value_elements = []
        running_string_length = 2  # accounts for array brackets in output string
        defined_max_tag_value_length = self.max_tag_value_length is not None and self.max_tag_value_length > 0

        for element in sequence:
            if isinstance(element, bool):
                tag_value_element = str(element).lower()
            elif isinstance(element, (int, float, str)):
                tag_value_element = str(element)
            elif element is None:
                tag_value_element = None
            else:
                continue

            if defined_max_tag_value_length:
                if tag_value_element is None:
                    running_string_length += 4  # null with no quotes
                else:
                    # + 2 accounts for string quotation marks
                    running_string_length += len(tag_value_element) + 2

                if tag_value_elements:
                    # accounts for ',' item separator
                    running_string_length += 1

                if running_string_length > self.max_tag_value_length:
                    break

            tag_value_elements.append(tag_value_element)

        return json.dumps(tag_value_elements, separators=(",", ":"))

    def _extract_tags_from_span(self, span: Span) -> dict[str, str]:
        """Collect every Zipkin tag a span contributes.

        Four groups are merged, later groups overwriting earlier ones on a key
        collision: the attributes of the span, the attributes of its resource,
        the name and version of its instrumentation scope, and the status and
        dropped counts.

        The scope name and version are written under both ``otel.scope.name``
        and ``otel.scope.version`` and the older ``otel.library.name`` and
        ``otel.library.version``. These four bypass the stringification and
        the truncation that the attribute groups go through, so a scope name
        or version longer than ``max_tag_value_length`` reaches the payload
        at its full length while every attribute value was cut to that
        limit.

        ``otel.status_code`` is written only when the status is not UNSET, and
        ``error`` is added alongside it when the status is ERROR, holding the
        status description or an empty string when there is none. Each of
        ``otel.dropped_attributes_count``, ``otel.dropped_events_count`` and
        ``otel.dropped_links_count`` appears only when that count is non-zero.

        Args:
            span: The span to read. It is expected to be an SDK span, since
                the resource, the instrumentation scope and the dropped counts
                are SDK attributes that the API span has no counterpart for.

        Returns:
            The merged tags.
        """
        tags = self._extract_tags_from_dict(span.attributes)
        if span.resource:
            tags.update(self._extract_tags_from_dict(span.resource.attributes))
        if span.instrumentation_scope is not None:
            tags.update(
                {
                    NAME_KEY: span.instrumentation_scope.name,
                    VERSION_KEY: span.instrumentation_scope.version,
                    _SCOPE_NAME_KEY: span.instrumentation_scope.name,
                    _SCOPE_VERSION_KEY: span.instrumentation_scope.version,
                }
            )
        if span.status.status_code is not StatusCode.UNSET:
            tags.update({"otel.status_code": span.status.status_code.name})
            if span.status.status_code is StatusCode.ERROR:
                tags.update({"error": span.status.description or ""})

        if span.dropped_attributes:
            tags.update({"otel.dropped_attributes_count": str(span.dropped_attributes)})

        if span.dropped_events:
            tags.update({"otel.dropped_events_count": str(span.dropped_events)})

        if span.dropped_links:
            tags.update({"otel.dropped_links_count": str(span.dropped_links)})

        return tags

    def _extract_annotations_from_events(self, events: list[Event] | None) -> list[dict] | None:
        """Convert span events into Zipkin annotations.

        Zipkin gives an annotation one timestamp and one string value, so the
        name of the event and all of its attributes are packed into that
        single value as a JSON object of the form ``{name: attributes}``, with
        keys sorted so that the output is stable. String attribute values are
        truncated to ``max_tag_value_length`` when that limit is positive;
        values of other types are left alone.

        Args:
            events: The events of the span, or ``None``.

        Returns:
            One annotation per event, in the order the events were recorded,
            or ``None`` when there are no events. The encoders omit the
            ``annotations`` field when this is ``None``.
        """
        if not events:
            return None

        annotations = []
        for event in events:
            attrs = {}
            for key, value in event.attributes.items():
                if isinstance(value, str) and self.max_tag_value_length is not None and self.max_tag_value_length > 0:
                    value = value[: self.max_tag_value_length]
                attrs[key] = value

            annotations.append(
                {
                    "timestamp": self._nsec_to_usec_round(event.timestamp),
                    "value": json.dumps({event.name: attrs}, sort_keys=True),
                }
            )
        return annotations

    @staticmethod
    def _nsec_to_usec_round(nsec: int) -> int:
        """Round nanoseconds to microseconds

        Timestamp in zipkin spans is int of microseconds.
        See: https://zipkin.io/pages/instrumenting.html

        Args:
            nsec: The value in nanoseconds. It is a wall clock timestamp for
                the start of a span or an event, and a difference of two such
                timestamps for a duration.

        Returns:
            The value in microseconds, rounded half up, so 1500 nanoseconds
            gives 2 microseconds.
        """
        return (nsec + 500) // 10**3


class JsonEncoder(Encoder):
    """Everything the JSON encoders share, independent of the API version.

    This fills in the parts of ``Encoder`` that the v1 and v2 JSON formats
    agree on: the media type, the shape of the request body, the encoding of
    ids as hexadecimal strings, and the encoding of the local endpoint. The
    per-span encoding differs between the two versions, so ``_encode_span`` is
    still abstract here and is supplied by ``JsonV1Encoder`` and
    ``JsonV2Encoder``.

    Args:
        max_tag_value_length: maximum length of an exported tag value. Values
          will be truncated to conform. Since values are serialized to a JSON
          list string, max_tag_value_length is honored at the element boundary.
    """

    @staticmethod
    def content_type():
        """Return the media type of a JSON Zipkin payload.

        Returns:
            Always ``"application/json"``, for both API versions.
        """
        return "application/json"

    def serialize(self, spans: Sequence[Span], local_endpoint: NodeEndpoint) -> str:
        """Encode a batch of spans as a JSON array.

        The local endpoint is encoded once and reused for every span of the
        batch.

        Args:
            spans: The ended spans to encode. An empty sequence gives ``"[]"``.
            local_endpoint: The network context of the node that recorded the
                spans.

        Returns:
            The JSON array of encoded spans, ready to be sent as the request
            body.
        """
        encoded_local_endpoint = self._encode_local_endpoint(local_endpoint)
        encoded_spans = []
        for span in spans:
            encoded_spans.append(self._encode_span(span, encoded_local_endpoint))
        return json.dumps(encoded_spans)

    @staticmethod
    def _encode_local_endpoint(local_endpoint: NodeEndpoint) -> dict:
        """Encode the local endpoint as a Zipkin endpoint object.

        Args:
            local_endpoint: The network context of the node that recorded the
                spans.

        Returns:
            A mapping always carrying ``serviceName``, and carrying ``ipv4``,
            ``ipv6`` and ``port`` only for those that the endpoint knows. The
            addresses are written in their textual form.
        """
        encoded_local_endpoint = {"serviceName": local_endpoint.service_name}
        if local_endpoint.ipv4 is not None:
            encoded_local_endpoint["ipv4"] = str(local_endpoint.ipv4)
        if local_endpoint.ipv6 is not None:
            encoded_local_endpoint["ipv6"] = str(local_endpoint.ipv6)
        if local_endpoint.port is not None:
            encoded_local_endpoint["port"] = local_endpoint.port
        return encoded_local_endpoint

    @staticmethod
    def _encode_span_id(span_id: int) -> str:
        """Encode a span id as Zipkin JSON spells it.

        Args:
            span_id: The span id, as the 64 bit integer the SDK holds.

        Returns:
            The id as 16 lowercase hexadecimal characters, zero padded.
        """
        return format_span_id(span_id)

    @staticmethod
    def _encode_trace_id(trace_id: int) -> str:
        """Encode a trace id as Zipkin JSON spells it.

        Args:
            trace_id: The trace id, as the 128 bit integer the SDK holds.

        Returns:
            The id as 32 lowercase hexadecimal characters, zero padded.
        """
        return format_trace_id(trace_id)
