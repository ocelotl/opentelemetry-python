# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Public entry point for span encoding.

Re-exports ``encode_spans``, which converts a sequence of
:class:`opentelemetry.sdk.trace.ReadableSpan` into the protobuf
``ExportTraceServiceRequest`` that an OTLP exporter sends. Import it from here
rather than from the ``_internal`` subpackage that defines it, because only this
module is part of the supported surface.
"""

from opentelemetry.exporter.otlp.proto.common._internal.trace_encoder import (
    encode_spans,
)

__all__ = ["encode_spans"]
