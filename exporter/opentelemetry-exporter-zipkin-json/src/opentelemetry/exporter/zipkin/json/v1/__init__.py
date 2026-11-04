# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Zipkin Export Encoders for JSON formats"""

from opentelemetry.exporter.zipkin.encoder import Encoder, JsonEncoder
from opentelemetry.trace import Span


# pylint: disable=W0223
class V1Encoder(Encoder):
    """The part of the v1 encoding that does not depend on the wire format.

    The v1 Zipkin API has no ``tags`` field. Span attributes are carried as
    binary annotations instead, and this supplies the conversion. Everything
    else is left to the concrete encoder, which is why this class is still
    abstract.

    Args:
        max_tag_value_length: maximum length of an exported tag value. Values
          will be truncated to conform. Since values are serialized to a JSON
          list string, max_tag_value_length is honored at the element boundary.
    """

    def _extract_binary_annotations(self, span: Span, encoded_local_endpoint: dict) -> list[dict]:
        """Convert the tags of a span into v1 binary annotations.

        Each tag becomes one annotation carrying the key, the value and a copy
        of the local endpoint, since v1 attaches the endpoint per annotation
        rather than once per span.

        String values are truncated to ``max_tag_value_length`` when that
        limit is set to a positive number. The tags that came from the
        attributes of the span and of its resource were already truncated
        when they were extracted, so truncating them again changes nothing.
        The scope, status and dropped count tags bypass that earlier
        truncation, so this is the only one they get, and the v1 payload can
        therefore carry a shorter value than the v2 payload for the same span.

        Args:
            span: The span whose tags to convert.
            encoded_local_endpoint: The already encoded local endpoint, placed
                in every annotation produced.

        Returns:
            One binary annotation per tag. Empty when the span contributes no
            tags.

        Raises:
            TypeError: If ``max_tag_value_length`` is ``None`` and the span
                contributes at least one tag whose value is a string, because
                the comparison against zero has no meaning for ``None``. A
                span that contributes no such tag never reaches the
                comparison. ``ZipkinExporter`` passes ``None`` whenever its
                own ``max_tag_value_length`` argument is left unset.
        """
        binary_annotations = []
        for tag_key, tag_value in self._extract_tags_from_span(span).items():
            if isinstance(tag_value, str) and self.max_tag_value_length > 0:
                tag_value = tag_value[: self.max_tag_value_length]
            binary_annotations.append(
                {
                    "key": tag_key,
                    "value": tag_value,
                    "endpoint": encoded_local_endpoint,
                }
            )
        return binary_annotations


class JsonV1Encoder(JsonEncoder, V1Encoder):
    """Zipkin Export Encoder for JSON v1 API

    API spec: https://github.com/openzipkin/zipkin-api/blob/master/zipkin-api.yaml

    Args:
        max_tag_value_length: maximum length of an exported tag value. Values
          will be truncated to conform. Since values are serialized to a JSON
          list string, max_tag_value_length is honored at the element boundary.
    """

    def _encode_span(self, span: Span, encoded_local_endpoint: dict) -> dict:
        """Encode one span in the v1 JSON format.

        ``traceId``, ``id``, ``name``, ``timestamp`` and ``duration`` are
        always written. ``annotations``, ``binaryAnnotations``, ``debug`` and
        ``parentId`` are written only when the span has something to put in
        them, which is what the specification asks for.

        The local endpoint is repeated inside every annotation and every
        binary annotation, because v1 has no per-span endpoint field.

        Args:
            span: The ended span to encode.
            encoded_local_endpoint: The already encoded local endpoint.

        Returns:
            The encoded span.

        Raises:
            TypeError: If ``max_tag_value_length`` is ``None`` and the span
                contributes at least one tag whose value is a string. See
                ``_extract_binary_annotations``.
        """
        context = span.get_span_context()

        encoded_span = {
            "traceId": self._encode_trace_id(context.trace_id),
            "id": self._encode_span_id(context.span_id),
            "name": span.name,
            "timestamp": self._nsec_to_usec_round(span.start_time),
            "duration": self._nsec_to_usec_round(span.end_time - span.start_time),
        }

        encoded_annotations = self._extract_annotations_from_events(span.events)
        if encoded_annotations is not None:
            for annotation in encoded_annotations:
                annotation["endpoint"] = encoded_local_endpoint
            encoded_span["annotations"] = encoded_annotations

        binary_annotations = self._extract_binary_annotations(span, encoded_local_endpoint)
        if binary_annotations:
            encoded_span["binaryAnnotations"] = binary_annotations

        debug = self._encode_debug(context)
        if debug:
            encoded_span["debug"] = debug

        parent_id = self._get_parent_id(span.parent)
        if parent_id is not None:
            encoded_span["parentId"] = self._encode_span_id(parent_id)

        return encoded_span
